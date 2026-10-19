import { createServer, type IncomingMessage, type ServerResponse } from "http";
import { readFileSync } from "fs";
import { join } from "path";
import { draftReply } from "./drafter";
import { autonomyStatus, loadFeedback, outcomeFor, recordFeedback } from "./feedback";
import type { CustomerEmail } from "./types";

const PORT = Number(process.env.INBOX_PORT ?? 3001);
const emails = JSON.parse(readFileSync(join(__dirname, "..", "data", "emails.json"), "utf-8")) as CustomerEmail[];

function json(res: ServerResponse, code: number, body: unknown): void {
  res.writeHead(code, { "Content-Type": "application/json" });
  res.end(JSON.stringify(body));
}
async function bodyOf(req: IncomingMessage): Promise<Record<string, unknown>> {
  const chunks: Buffer[] = [];
  for await (const c of req) chunks.push(c as Buffer);
  try { return JSON.parse(Buffer.concat(chunks).toString() || "{}") as Record<string, unknown>; } catch { return {}; }
}

const sentIds = new Set<string>(); // idempotency: a retry must never double-send

const server = createServer(async (req, res) => {
  const url = req.url ?? "/";
  try {
    if (req.method === "GET" && url === "/health") return json(res, 200, { status: "ok", emails: emails.length });
    if (req.method === "GET" && url === "/api/emails") return json(res, 200, emails);
    if (req.method === "GET" && url === "/api/autonomy") return json(res, 200, autonomyStatus());
    if (req.method === "GET" && url === "/api/feedback") return json(res, 200, loadFeedback());
    if (req.method === "POST" && url === "/api/draft") {
      const b = await bodyOf(req);
      const email = emails.find((e) => e.id === String(b["emailId"] ?? ""));
      if (!email) return json(res, 404, { error: "email not found" });
      return json(res, 200, await draftReply(email));
    }
    if (req.method === "POST" && url === "/api/review") {
      const b = await bodyOf(req);
      const emailId = String(b["emailId"] ?? "");
      const generated = String(b["generatedDraft"] ?? "");
      const finalSent = String(b["finalSent"] ?? "");
      const rejected = b["rejected"] === true;
      if (!rejected && sentIds.has(emailId)) return json(res, 409, { error: "already sent (idempotency guard)" });
      const outcome = outcomeFor(generated, finalSent, rejected);
      recordFeedback({
        emailId, category: (String(b["category"] ?? "unknown") as CustomerEmail["expectedCategory"]) ?? "unknown",
        generatedDraft: generated, finalSent, outcome,
        reason: String(b["reason"] ?? ""), promptVersion: String(b["promptVersion"] ?? "inbox-draft-v1"),
        at: new Date().toISOString(),
      });
      if (!rejected) sentIds.add(emailId);
      return json(res, 200, { recorded: true, outcome, note: "sent = simulated send in capstone build (see README)" });
    }
    if (req.method === "GET" && url === "/") {
      res.writeHead(200, { "Content-Type": "text/html" });
      return res.end(UI);
    }
    return json(res, 404, { error: "not found" });
  } catch (e) {
    return json(res, 500, { error: String(e) });
  }
});

const UI = `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Inbox Agent</title><style>body{font-family:system-ui,sans-serif;max-width:900px;margin:2rem auto;padding:0 1rem;color:#17202a}
select,textarea{width:100%;padding:.6rem}button{background:#14532d;color:#fff;border:0;padding:.6rem 1rem;border-radius:6px;cursor:pointer;margin-right:.4rem}
button.alt{background:#666}.card{background:#f4f6f5;border-radius:8px;padding:1rem;margin-top:1rem;white-space:pre-wrap}small{color:#666}</style></head>
<body><h1>📥 Inbox Agent</h1><p>Pick an email → draft (grounded via Task 1 API) → edit / approve / reject. Every decision is recorded; 20 consecutive unedited sends of one kind makes it <em>eligible</em> for a monitored auto-send trial (refunds &amp; complaints: never).</p>
<select id="sel"></select><div class="card" id="orig">Select an email…</div>
<p><button onclick="draft()">Draft reply</button> <small id="st"></small></p>
<textarea id="reply" rows="10" placeholder="Draft appears here — edit freely before sending"></textarea>
<p><button onclick="review(false)">Approve &amp; send (simulated)</button><button class="alt" onclick="review(true)">Reject</button></p>
<div class="card" id="meta"></div><div class="card" id="auto"></div>
<script>
let emails=[], cur=null, generated="";
async function init(){emails=await(await fetch('/api/emails')).json();
const s=document.getElementById('sel');s.innerHTML=emails.map(e=>'<option value="'+e.id+'">'+e.id+' — '+e.subject+'</option>').join('');
s.onchange=show;show();showAuto();}
function show(){cur=emails.find(e=>e.id===document.getElementById('sel').value);
document.getElementById('orig').textContent='From: '+cur.from+'\\nSubject: '+cur.subject+'\\n\\n'+cur.body;}
async function draft(){document.getElementById('st').textContent='Asking Knowledge Brain…';
const d=await(await fetch('/api/draft',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({emailId:cur.id})})).json();
document.getElementById('st').textContent='';generated=d.suggestedReply;window._d=d;
document.getElementById('reply').value=d.suggestedReply;
document.getElementById('meta').textContent='Category: '+d.category+' · Risk: '+d.risk+' · Knowledge: '+d.knowledgeStatus+'\\nEvidence: '+(d.evidence.map(e=>e.title).join('; ')||'none')+'\\nNext: '+d.nextAction+'\\nPrompt: '+d.promptVersion;}
async function review(rejected){const d=window._d;if(!d){alert('Draft first');return;}
const r=await(await fetch('/api/review',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({emailId:cur.id,generatedDraft:generated,finalSent:document.getElementById('reply').value,rejected,category:d.category,promptVersion:d.promptVersion,reason:''})})).json();
document.getElementById('st').textContent=JSON.stringify(r);showAuto();}
async function showAuto(){const a=await(await fetch('/api/autonomy')).json();
document.getElementById('auto').textContent='Autonomy streaks:\\n'+Object.entries(a).map(([k,v])=>k+': '+v.streak+'/20 — '+v.reason).join('\\n');}
init();
</script></body></html>`;

server.listen(PORT, "0.0.0.0", () => console.log(`Inbox Agent on http://0.0.0.0:${PORT} (KB: ${process.env.KNOWLEDGE_BRAIN_URL ?? "http://127.0.0.1:8000"})`));
