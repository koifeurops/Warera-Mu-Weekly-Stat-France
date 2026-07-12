const fs   = require('fs');
const path = require('path');

// ============================================
// CONFIGURATION
// ============================================

const API_KEY = fs.readFileSync(path.join(__dirname, 'data/api_key.txt'), 'utf8').trim();

// data/mu_id.txt: one MU id per line.
// Blank lines and lines starting with # are ignored.
// An inline comment after the id (e.g. "abc123 # Spectre") is also stripped.
const MU_IDS = fs.readFileSync(path.join(__dirname, 'data/mu_id.txt'), 'utf8')
  .split('\n')
  .map(line => line.split('#')[0].trim())
  .filter(line => line.length > 0);

const BASE_URL       = 'https://api2.warera.io/trpc';
const CONCURRENT     = 8;   // parallel user-profile requests
const RETRY_ATTEMPTS = 5;   // retries on 429 rate-limit
const RETRY_BASE_MS  = 1000; // base back-off delay in ms

// ============================================
// CORE: tRPC GET caller
// The WarEra API uses GET with params encoded as ?input=<json>
// Auth: X-API-Key header (or Cookie: jwt=... if you have a session token)
// ============================================

async function trpc(procedure, params = {}) {
  const input    = encodeURIComponent(JSON.stringify(params));
  const url      = `${BASE_URL}/${procedure}?input=${input}`;
  const headers  = {
    'Origin':     'https://app.warera.io',
    'Referer':    'https://app.warera.io/',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36',
    'X-API-Key':  API_KEY,
  };

  for (let attempt = 0; attempt < RETRY_ATTEMPTS; attempt++) {
    const res = await fetch(url, { headers });

    if (res.status === 429) {
      const wait = RETRY_BASE_MS * 2 ** attempt;
      console.warn(`   ⏳ Rate-limited — waiting ${wait}ms (attempt ${attempt + 1}/${RETRY_ATTEMPTS})`);
      await sleep(wait);
      continue;
    }

    if (!res.ok) {
      const text = await res.text();
      throw new Error(`HTTP ${res.status} on ${procedure}: ${text.slice(0, 200)}`);
    }

    const data = await res.json();

    // tRPC wraps errors even on HTTP 200
    if (data.error && !data.result) {
      const msg = data.error?.json?.message ?? JSON.stringify(data.error);
      throw new Error(`tRPC error on ${procedure}: ${msg}`);
    }

    return data.result.data;
  }

  throw new Error(`${procedure} failed after ${RETRY_ATTEMPTS} attempts (rate-limited)`);
}

// ============================================
// HELPERS
// ============================================

function sleep(ms) {
  return new Promise(resolve => setTimeout(resolve, ms));
}

// Run tasks in chunks of `size` concurrently
async function mapConcurrent(items, size, fn) {
  const results = [];
  for (let i = 0; i < items.length; i += size) {
    const chunk = items.slice(i, i + size);
    const batch = await Promise.all(chunk.map(fn));
    results.push(...batch);
    if (i + size < items.length) await sleep(200); // small pause between batches
  }
  return results;
}

// ============================================
// STEP 1: Fetch MU info (name, member IDs, etc.)
// Endpoint: mu.getById  →  { muId }
// ============================================

async function getMu(muId) {
  console.log(`\n📋 Fetching MU info for: ${muId}`);
  const mu = await trpc('mu.getById', { muId });
  console.log(`   ✓ MU name:    ${mu.name ?? '(unknown)'}`);
  console.log(`   ✓ Member IDs: ${(mu.members ?? []).length} found`);
  return mu;
}

// ============================================
// STEP 2: Fetch full profile for a single user
// Endpoint: user.getUserLite  →  { userId }
// ============================================

async function getUserLite(userId) {
  try {
    return await trpc('user.getUserLite', { userId });
  } catch (err) {
    console.warn(`   ⚠️  Could not fetch user ${userId}: ${err.message}`);
    return { _id: userId, _fetchError: err.message };
  }
}

// ============================================
// STEP 3: Fetch all member profiles
// ============================================

async function getMuMembers(memberIds) {
  const total = memberIds.length;
  console.log(`\n👥 Fetching profiles for ${total} member(s)…`);

  let done = 0;
  const users = await mapConcurrent(memberIds, CONCURRENT, async (userId) => {
    const user = await getUserLite(userId);
    done++;
    process.stdout.write(`\r   Progress: ${done}/${total}`);
    return user;
  });

  console.log('\n   ✓ Done');
  return users;
}

// ============================================
// STEP 4: Fetch one MU end-to-end (info + members)
// Isolated per-MU so one bad id doesn't abort the rest.
// ============================================

async function fetchOneMu(muId) {
  try {
    const mu = await getMu(muId);
    const memberIds = mu.members ?? [];

    if (memberIds.length === 0) {
      console.warn(`\n⚠️  MU ${muId} has no members listed in the API response.`);
      return { mu, members: [] };
    }

    const members = await getMuMembers(memberIds);
    return { mu, members };
  } catch (err) {
    console.error(`\n❌ Failed to fetch MU ${muId}: ${err.message}`);
    return { mu: { _id: muId, _fetchError: err.message }, members: [] };
  }
}

// ============================================
// SAVE TO JSON
// ============================================

function saveJson(muResults) {
  const output = {
    metadata: {
      fetchedAt: new Date().toISOString(),
      totalMus:  muResults.length,
      muIds:     MU_IDS,
      apiKey:    '***HIDDEN***',
    },
    mus: muResults, // array of { mu, members }
  };

  const filepath = path.join(process.cwd(), 'data.json');
  fs.writeFileSync(filepath, JSON.stringify(output, null, 2), 'utf8');
  console.log(`\n✓ Saved → ${filepath}`);
  return filepath;
}

// ============================================
// MAIN
// ============================================

async function main() {
  console.log('═'.repeat(60));
  console.log(' WarEra — Fetch all members of one or more Military Units');
  console.log('═'.repeat(60));
  console.log(` MU IDs (${MU_IDS.length}): ${MU_IDS.join(', ')}`);
  console.log('═'.repeat(60));

  if (MU_IDS.length === 0) {
    console.error('\n❌ No MU ids found in data/mu_id.txt. Add at least one id (one per line).');
    process.exit(1);
  }

  const muResults = [];
  for (const muId of MU_IDS) {
    const result = await fetchOneMu(muId);
    muResults.push(result);
  }

  saveJson(muResults);

  // Quick summary
  console.log('\n📊 Summary:');
  for (const { mu, members } of muResults) {
    console.log(`   • ${mu.name ?? mu._id}: ${members.length} member(s)`);
  }

  console.log('\n' + '═'.repeat(60));
  console.log(' Done.');
}

main().catch(err => {
  console.error('\n❌ Fatal error:', err.message);
  process.exit(1);
});
