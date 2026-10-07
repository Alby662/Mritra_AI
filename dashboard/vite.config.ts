import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';
import type { Plugin } from 'vite';
import fs from 'node:fs';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const currentDir = path.dirname(fileURLToPath(import.meta.url));

function mritraApiPlugin(): Plugin {
  return {
    name: 'mritra-api-server',
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url || '';

        // API Endpoint: /api/results/summary
        if (url === '/api/results/summary') {
          res.setHeader('Content-Type', 'application/json');
          try {
            const rootDir = path.resolve(currentDir, '..');
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

        // API Endpoint: /api/runs
        if (url === '/api/runs') {
          res.setHeader('Content-Type', 'application/json');
          try {
            const rootDir = path.resolve(currentDir, '..');
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

                let manifest = null;
                if (hasManifest) {
                  try {
                    manifest = JSON.parse(fs.readFileSync(manifestPath, 'utf-8'));
                  } catch {}
                }

                return {
                  runId: e.name,
                  hasManifest,
                  hasEval,
                  partition: manifest?.partition || 'P1',
                  configSha256: manifest?.config_sha256 || '',
                  timestamp: manifest?.t0 || e.name,
                  featureCount: manifest?.feature_columns?.C1?.['0']?.length || 14
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
    host: true
  }
});
