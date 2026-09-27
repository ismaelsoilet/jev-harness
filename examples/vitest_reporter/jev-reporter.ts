import type { Reporter, TestCase } from 'vitest/node';
import { triageTestFailure } from '@ismaelsoilet/jev-harness';

/**
 * JevVitestReporter
 * 
 * Transparent Vitest failure interceptor hook.
 * Intercepts test failures in < 500µs:
 * - If deterministic (missing package, flaky port/timeout): outputs the exact fix (0 LLM tokens).
 * - If deep logic: allows normal test reporting for System 2 escalation.
 * 
 * Usage in vitest.config.ts:
 * ```ts
 * import { defineConfig } from 'vitest/config';
 * import JevVitestReporter from './examples/vitest_reporter/jev-reporter';
 * 
 * export default defineConfig({
 *   test: {
 *     reporters: ['default', new JevVitestReporter()],
 *   },
 * });
 * ```
 */
export default class JevVitestReporter implements Reporter {
  async onTestCaseResult(testCase: TestCase): Promise<void> {
    if (testCase.result?.state === 'fail') {
      const errorMsg =
        testCase.result.errors
          ?.map((e) => e.stack || e.message)
          .filter(Boolean)
          .join('\n') || '';

      if (!errorMsg.trim()) return;

      try {
        const triage = await triageTestFailure(errorMsg);
        if (triage.skipLlm) {
          console.log('\n======================================================================');
          console.log('⚡ [JEV HARNESS - SYSTEM 1.5 DETERMINISTIC TRIAGE]');
          console.log(`Test:           ${testCase.name}`);
          console.log(`Category:       ${triage.category.toUpperCase()}`);
          console.log(`Skip LLM Call:  YES (0 tokens required)`);
          console.log(`Action:         ${triage.actionRecommendation}`);
          if (triage.recovery && Array.isArray(triage.recovery.commands) && triage.recovery.commands.length > 0) {
            console.log(`Suggested Fix:  ${triage.recovery.commands.join(' && ')}`);
          }
          console.log('======================================================================\n');
        }
      } catch {
        // Fallback silently if offline or unhandled
      }
    }
  }
}
