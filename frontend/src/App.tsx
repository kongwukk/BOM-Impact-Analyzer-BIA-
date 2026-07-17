import { FormEvent, useState } from "react";
import { AlertTriangle, Boxes, Database, FileSpreadsheet, Search, Upload } from "lucide-react";
import { getImpact, ImpactResult, uploadBom } from "./api";

type View = "dashboard" | "upload" | "impact";

export default function App() {
  const [view, setView] = useState<View>("dashboard");
  const [partNumber, setPartNumber] = useState("");
  const [impact, setImpact] = useState<ImpactResult | null>(null);
  const [error, setError] = useState("");
  const [busy, setBusy] = useState(false);
  const [uploadMessage, setUploadMessage] = useState("");

  async function searchImpact(event: FormEvent) {
    event.preventDefault();
    setBusy(true);
    setError("");
    try {
      setImpact(await getImpact(partNumber.trim()));
    } catch (reason) {
      setImpact(null);
      setError(reason instanceof Error ? reason.message : "查询失败");
    } finally {
      setBusy(false);
    }
  }

  async function importFile(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const form = new FormData(event.currentTarget);
    const file = form.get("file");
    if (!(file instanceof File) || !file.name) return;
    setBusy(true);
    setError("");
    setUploadMessage("");
    try {
      const result = await uploadBom(file, String(form.get("productCode") || ""));
      setUploadMessage(`导入成功：${result.components_imported} 个元器件，跳过 ${result.duplicates_skipped} 条重复记录。`);
    } catch (reason) {
      setError(reason instanceof Error ? reason.message : "导入失败");
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="shell">
      <aside>
        <div className="brand"><Boxes size={27} /><span>BOM 智管</span></div>
        <nav>
          <button className={view === "dashboard" ? "active" : ""} onClick={() => setView("dashboard")}><Database />总览</button>
          <button className={view === "upload" ? "active" : ""} onClick={() => setView("upload")}><Upload />BOM 导入</button>
          <button className={view === "impact" ? "active" : ""} onClick={() => setView("impact")}><Search />影响查询</button>
        </nav>
        <div className="aside-note">MVP · v0.1.0</div>
      </aside>
      <main>
        <header><div><small>BOM IMPACT ANALYZER</small><h1>{view === "dashboard" ? "系统总览" : view === "upload" ? "BOM 数据导入" : "元器件影响查询"}</h1></div><span className="status"><i />服务就绪</span></header>

        {error && <div className="error"><AlertTriangle size={18} />{error}</div>}
        {view === "dashboard" && <Dashboard navigate={setView} />}
        {view === "upload" && (
          <section className="panel narrow">
            <div className="panel-title"><FileSpreadsheet /><div><h2>导入 Excel BOM</h2><p>支持 .xlsx / .xlsm，系统会自动映射常见中英文列名。</p></div></div>
            <form className="upload-form" onSubmit={importFile}>
              <label>产品型号（可选）<input name="productCode" placeholder="默认使用文件名" /></label>
              <label className="dropzone"><Upload size={32} /><strong>选择 BOM 文件</strong><span>最大 20 MB</span><input required name="file" type="file" accept=".xlsx,.xlsm" /></label>
              <button className="primary" disabled={busy}>{busy ? "正在导入…" : "开始导入"}</button>
            </form>
            {uploadMessage && <div className="success">{uploadMessage}</div>}
          </section>
        )}
        {view === "impact" && (
          <section className="panel">
            <form className="search-form" onSubmit={searchImpact}>
              <Search /><input required value={partNumber} onChange={(event) => setPartNumber(event.target.value)} placeholder="输入完整元器件型号，如 STM32F103C8T6" /><button className="primary" disabled={busy}>{busy ? "查询中…" : "查询影响"}</button>
            </form>
            {impact ? <ImpactTable impact={impact} /> : <div className="empty"><Search size={42} /><h3>从一个元器件开始</h3><p>精确查询它出现在哪些产品 BOM 中。</p></div>}
          </section>
        )}
      </main>
    </div>
  );
}

function Dashboard({ navigate }: { navigate: (view: View) => void }) {
  return <><div className="hero"><div><span className="eyebrow">STRUCTURED DATA · DETERMINISTIC RESULTS</span><h2>让每一次元器件变更<br />都有清晰的影响边界</h2><p>集中管理分散的 Excel BOM，快速定位受影响产品，为停产与替代决策提供可信数据。</p><button className="primary" onClick={() => navigate("upload")}>导入第一份 BOM</button></div><div className="hero-mark"><Boxes /></div></div><div className="cards"><article><FileSpreadsheet /><strong>BOM 数据中心</strong><p>标准化导入与统一归档</p></article><article><Search /><strong>精确影响查询</strong><p>按器件型号追溯产品</p></article><article><AlertTriangle /><strong>生命周期风险</strong><p>EOL / NRND 风险分级</p></article></div></>;
}

function ImpactTable({ impact }: { impact: ImpactResult }) {
  return <div className="results"><div className="summary"><div><small>元器件型号</small><strong>{impact.part_number}</strong><span>{impact.manufacturer || "制造商未知"} · {impact.lifecycle_status}</span></div><div className={`risk ${impact.risk_level.toLowerCase()}`}>{impact.risk_level}</div><div className="count"><strong>{impact.total_affected}</strong><span>受影响产品</span></div></div><div className="table-wrap"><table><thead><tr><th>产品型号</th><th>产品名称</th><th>数量</th><th>位号</th><th>关键器件</th></tr></thead><tbody>{impact.affected_products.map((product) => <tr key={product.product_code}><td><b>{product.product_code}</b></td><td>{product.product_name}</td><td>{product.quantity}</td><td>{product.reference || "—"}</td><td>{product.is_critical ? "是" : "否"}</td></tr>)}</tbody></table></div></div>;
}

