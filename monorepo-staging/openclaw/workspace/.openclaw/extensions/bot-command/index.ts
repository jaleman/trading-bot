import { execFile } from "node:child_process";
import { homedir } from "node:os";
import path from "node:path";
import { promisify } from "node:util";

const execFileAsync = promisify(execFile);
const routerScript = path.join(
  homedir(),
  "trading-bot",
  "monorepo-staging",
  "scripts",
  "run_trading_bot_telegram_command.sh",
);

function formatCommand(args?: string): string {
  const trimmed = (args ?? "").trim();
  return trimmed ? `bot ${trimmed}` : "bot list";
}

function formatReply(stdout?: string, stderr?: string): string {
  const text = (stdout ?? "").trim() || (stderr ?? "").trim();
  return text || "No output.";
}

export default function register(api: {
  logger?: { info?: (message: string) => void };
  registerCommand: (command: {
    name: string;
    description: string;
    acceptsArgs?: boolean;
    requireAuth?: boolean;
    handler: (ctx: { args?: string; channel?: string; senderId?: string }) => Promise<{ text: string }>;
  }) => void;
}) {
  api.registerCommand({
    name: "bot",
    description: "Trading bot operator router. Usage: /bot list|summary|pending|status|balance|holdings|info <TICKER>|sync|restart",
    acceptsArgs: true,
    requireAuth: true,
    handler: async (ctx) => {
      const commandLine = formatCommand(ctx.args);
      api.logger?.info?.(
        `bot-command: /bot invoked channel=${ctx.channel ?? "unknown"} sender=${ctx.senderId ?? "unknown"} command=${commandLine}`,
      );
      try {
        const result = await execFileAsync(routerScript, [commandLine], {
          encoding: "utf8",
          maxBuffer: 1024 * 1024,
        });
        return { text: formatReply(result.stdout, result.stderr) };
      } catch (error) {
        const failure = error as Error & { stdout?: string; stderr?: string };
        return { text: formatReply(failure.stdout, failure.stderr) || failure.message };
      }
    },
  });
}