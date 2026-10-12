import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import fs from 'node:fs';
import path from 'node:path';
import https from 'node:https';
import { fileURLToPath } from 'node:url';

const currentDir = path.dirname(fileURLToPath(import.meta.url));
const rootDir = path.resolve(currentDir, '..');
const secretsDir = path.join(rootDir, 'secrets');

// Load mTLS client certificates
let httpsAgent: https.Agent | undefined;
try {
  const caPath = path.join(secretsDir, 'ca.crt');
  const certPath = path.join(secretsDir, 'B1.crt');
  const keyPath = path.join(secretsDir, 'B1.key');

  if (fs.existsSync(caPath) && fs.existsSync(certPath) && fs.existsSync(keyPath)) {
    httpsAgent = new https.Agent({
      ca: fs.readFileSync(caPath),
      cert: fs.readFileSync(certPath),
      key: fs.readFileSync(keyPath),
      rejectUnauthorized: false, // Local self-signed CA
    });
    console.log('[mTLS] Initialized https.Agent with secrets/ca.crt, secrets/B1.crt, secrets/B1.key');
  } else {
    console.warn('[mTLS] Warning: secrets directory missing ca.crt, B1.crt, or B1.key');
  }
} catch (e: any) {
  console.error('[mTLS] Failed to load certificates:', e.message);
}

function proxyToBackend(targetBase: string, targetPath: string, req: any, res: any) {
  if (!httpsAgent) {
    res.statusCode = 500;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({ error: 'mTLS Agent not configured. Certificates missing in secrets/.' }));
    return;
  }

  const targetUrl = new URL(targetPath, targetBase);
  const options: https.RequestOptions = {
    hostname: targetUrl.hostname,
    port: targetUrl.port,
    path: targetUrl.pathname + targetUrl.search,
    method: req.method,
    headers: {
      ...req.headers,
      host: `${targetUrl.hostname}:${targetUrl.port}`,
    },
    agent: httpsAgent,
    rejectUnauthorized: false,
  };

  const proxyReq = https.request(options, (proxyRes) => {
    res.writeHead(proxyRes.statusCode || 200, proxyRes.headers);
    proxyRes.pipe(res, { end: true });
  });

  proxyReq.on('error', (err) => {
    res.statusCode = 502;
    res.setHeader('Content-Type', 'application/json');
    res.end(JSON.stringify({
      error: 'mTLS Proxy Connection Failed',
      message: err.message,
      target: targetUrl.toString(),
      hint: 'Ensure backend docker containers are running on ports 8000-8004 and 8443 (docker compose up in deploy/).'
    }));
  });

  req.pipe(proxyReq, { end: true });
}

function mritraApiPlugin(): Plugin {
  return {
    name: 'mritra-api-server',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const rawUrl = req.url || '';
        const parsedUrl = new URL(rawUrl, 'http://localhost:5173');
        const pathname = parsedUrl.pathname;

        // 1. Hero Chain Demo Endpoint: /api/hero-chain
        if (pathname === '/api/hero-chain' || pathname === '/api/hero-chain/268') {
          res.setHeader('Content-Type', 'application/json');
          const heroPath = path.join(rootDir, 'results', 'demo_hero_chain.json');
          if (fs.existsSync(heroPath)) {
            res.end(fs.readFileSync(heroPath, 'utf-8'));
          } else {
            res.statusCode = 404;
            res.end(JSON.stringify({ error: 'results/demo_hero_chain.json not found' }));
          }
          return;
        }

        // 2. Summary Endpoint: /api/results/summary
        if (pathname === '/api/results/summary') {
          res.setHeader('Content-Type', 'application/json');
          try {
            const reconPath = path.join(rootDir, 'results', 'reconciliation_injection.json');
            const h1Path = path.join(rootDir, 'results', 'h1.json');
            const auditPath = path.join(rootDir, 'results', 'config_audit.json');
            const dataStatsPath = path.join(rootDir, 'results', 'data_stats.json');

            const reconData = fs.existsSync(reconPath) ? JSON.parse(fs.readFileSync(reconPath, 'utf-8')) : null;
            const h1Data = fs.existsSync(h1Path) ? JSON.parse(fs.readFileSync(h1Path, 'utf-8')) : null;
            const auditData = fs.existsSync(auditPath) ? JSON.parse(fs.readFileSync(auditPath, 'utf-8')) : null;
            const dataStats = fs.existsSync(dataStatsPath) ? JSON.parse(fs.readFileSync(dataStatsPath, 'utf-8')) : null;

            res.end(JSON.stringify({
              success: true,
              timestamp: new Date().toISOString(),
              data_stats: dataStats ? {
                rows_raw: dataStats.rows_raw,
                rows_loaded: dataStats.rows_loaded,
                distinct_banks: dataStats.distinct_banks,
                distinct_accounts: dataStats.distinct_accounts,
                laundering_txns: dataStats.laundering_txns,
                laundering_rate: dataStats.laundering_rate,
                splits: dataStats.splits,
                txns_per_day: dataStats.txns_per_day,
              } : null,
              reconciliation: reconData,
              h1: h1Data ? {
                pattern_rows: h1Data.match?.pattern_rows,
                matched_pattern_rows: h1Data.match?.matched_pattern_rows,
                match_rate: h1Data.match?.pattern_to_transaction_match_rate,
                laundering_txns: h1Data.match?.laundering_txns_total,
                laundering_txns_not_in_pattern: h1Data.match?.laundering_txns_not_in_pattern,
                config_sha256: h1Data.config_sha256,
              } : null,
              audit: auditData ? {
                config_sha256: auditData.config_sha256,
                c1_features: auditData.configs?.C1?.feature_columns?.length || 0,
                c3_features: auditData.configs?.C3?.feature_columns?.length || 0,
                c4_features: auditData.configs?.C4?.feature_columns?.length || 0,
              } : null
            }));
            return;
          } catch (err: any) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: err.message }));
            return;
          }
        }

        // 3. Runs Catalog Endpoint: /api/runs
        if (pathname === '/api/runs') {
          res.setHeader('Content-Type', 'application/json');
          try {
            const runsDir = path.join(rootDir, 'results', 'runs');
            if (!fs.existsSync(runsDir)) {
              res.end(JSON.stringify({ runs: [] }));
              return;
            }

            const entries = fs.readdirSync(runsDir, { withFileTypes: true });
            const runFolders = entries
              .filter(e => e.isDirectory() && !e.name.startsWith('.'))
              .map(e => {
                const manifestPath = path.join(runsDir, e.name, 'manifest.json');
                const evalPath = path.join(runsDir, e.name, 'eval.json');
                const hasManifest = fs.existsSync(manifestPath);
                const hasEval = fs.existsSync(evalPath);

                let manifest: any = null;
                let evalData: any = null;
                if (hasManifest) {
                  try {
                    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
                  } catch {}
                }
                if (hasEval) {
                  try {
                    evalData = JSON.parse(fs.readFileSync(evalPath, 'utf-8'));
                  } catch {}
                }

                return {
                  runId: e.name,
                  hasManifest,
                  hasEval,
                  partition: manifest?.partition || 'P1',
                  configSha256: manifest?.config_sha256 || '',
                  timestamp: manifest?.t0 || e.name,
                  featureCount: manifest?.feature_columns?.C1?.['0']?.length || 229,
                  modelsCount: manifest?.train_run_info ? Object.values(manifest.train_run_info).reduce((acc: number, cfg: any) => acc + Object.keys(cfg).length, 0) : 33,
                  evalSummary: evalData ? {
                    split: evalData.split,
                    c1_cross_bank_f1: evalData.c1_cross_bank?.['42']?.f1_minority,
                    c4_oracle_f1: evalData.results?.C4?.all?.['42']?.primary?.f1_minority,
                    c4_oracle_pr_auc: evalData.results?.C4?.all?.['42']?.primary?.pr_auc
                  } : null
                };
              });

            res.end(JSON.stringify({ runs: runFolders }));
            return;
          } catch (err: any) {
            res.statusCode = 500;
            res.end(JSON.stringify({ error: err.message }));
            return;
          }
        }

        // 4. mTLS Reverse Proxy for Bank Service (Default Bank B1 on 8001)
        if (pathname.startsWith('/api/bank/')) {
          const subPath = rawUrl.replace(/^\/api\/bank/, '');
          proxyToBackend('https://127.0.0.1:8001', subPath, req, res);
          return;
        }

        // 5. mTLS Reverse Proxy for Enclave Service (Port 8443)
        if (pathname.startsWith('/api/enclave/')) {
          const subPath = rawUrl.replace(/^\/api\/enclave/, '');
          proxyToBackend('https://127.0.0.1:8443', subPath, req, res);
          return;
        }

        // 6. Direct /v1/* route mapping (defaults to Bank B1 or Enclave based on prefix)
        if (pathname.startsWith('/v1/log/')) {
          proxyToBackend('https://127.0.0.1:8443', rawUrl, req, res);
          return;
        }
        if (pathname.startsWith('/v1/cases') || pathname.startsWith('/v1/exposure/')) {
          proxyToBackend('https://127.0.0.1:8001', rawUrl, req, res);
          return;
        }

        next();
      });
    }
  };
}

// https://vite.dev/config/
export default defineConfig({
  plugins: [react(), mritraApiPlugin()],
  server: {
    port: 5173,
    host: true,
    proxy: httpsAgent ? {
      '/api/bank': {
        target: 'https://127.0.0.1:8001',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/bank/, ''),
        secure: false,
        agent: httpsAgent,
      },
      '/api/enclave': {
        target: 'https://127.0.0.1:8443',
        changeOrigin: true,
        rewrite: (p) => p.replace(/^\/api\/enclave/, ''),
        secure: false,
        agent: httpsAgent,
      },
    } : {}
  }
});
