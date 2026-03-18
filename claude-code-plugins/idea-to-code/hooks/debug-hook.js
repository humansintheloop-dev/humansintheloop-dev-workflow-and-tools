#!/usr/bin/env node
/**
 * Debug script to see what hook data is being received
 */

const fs = require('fs');
const path = require('path');

// Read JSON input from stdin
let input = '';
process.stdin.setEncoding('utf8');

process.stdin.on('data', (chunk) => {
  input += chunk;
});

process.stdin.on('end', () => {
  try {
    const data = JSON.parse(input);

    // Write to a debug file
    const debugFile = path.join(process.cwd(), '.claude', 'hook-debug.log');
    const timestamp = new Date().toISOString();
    const logEntry = `\n=== ${timestamp} ===\n${JSON.stringify(data, null, 2)}\n`;

    fs.mkdirSync(path.dirname(debugFile), { recursive: true });
    fs.appendFileSync(debugFile, logEntry);

    // Also log transcript content if available
    if (data.transcript_path && fs.existsSync(data.transcript_path)) {
      const transcriptContent = fs.readFileSync(data.transcript_path, 'utf8');
      fs.appendFileSync(debugFile, `\n--- Transcript Content ---\n${transcriptContent.slice(0, 2000)}\n`);
    }

  } catch (error) {
    console.error(`[debug-hook] Error: ${error.message}`);
  }
});
