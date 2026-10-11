// Backend Node.js 18+: import { predictIssue } from './ml_client.mjs';
import { pathToFileURL } from "node:url";

const API_URL = (process.env.CAMPUSPULSE_ML_API_URL || "http://127.0.0.1:8001")
  .replace(/\/+$/, "");

export async function predictIssue(type, describe) {
  const response = await fetch(`${API_URL}/predict`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ Type: type, Describe: describe }),
    signal: AbortSignal.timeout(10000),
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(`ML API trả HTTP ${response.status}: ${JSON.stringify(result.detail)}`);
  }
  return result;
}

if (process.argv[1] && import.meta.url === pathToFileURL(process.argv[1]).href) {
  const result = await predictIssue(
    "Mạng và đường truyền", "wifi tầng 4 bắt được mà load mãi không xong"
  );
  console.log(JSON.stringify(result, null, 2));
}
