# Jev Harness - Vitest Failure Interceptor Reporter

This reporter integrates **Jev Harness** into Vitest, providing immediate, zero-token deterministic triage for failures.

## Quick Setup

1. Install `@ismaelsoilet/jev-harness`:
```bash
npm install -D @ismaelsoilet/jev-harness
```

2. Register `JevVitestReporter` in your `vitest.config.ts`:
```typescript
import { defineConfig } from 'vitest/config';
import JevVitestReporter from './examples/vitest_reporter/jev-reporter';

export default defineConfig({
  test: {
    reporters: ['default', new JevVitestReporter()],
  },
});
```

3. Run your tests:
```bash
npx vitest run
```

When a missing package (`Cannot find module`, `TS2307`) or a transient connection issue occurs, `jev-harness` intercepts the failure locally in < 500µs and prints the exact shell command to fix it, preventing AI coding agents from burning 50,000 tokens on a trivial issue.
