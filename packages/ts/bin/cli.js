#!/usr/bin/env node
import { runCli } from "../dist/cli.js";

runCli()
  .then((code) => process.exit(code))
  .catch((err) => {
    console.error(`Error: ${err?.message ?? err}`);
    process.exit(2);
  });
