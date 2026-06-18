const fs = require("fs");
const path = require("path");

const INPUT_DIR = path.resolve(__dirname, "../tmp/stitch_screens");
const SCREENS = {
  ManagerDashboard: { role: "manager", activeNav: "dashboard", outputName: "ManagerDashboard" },
  MenuManagement: { role: "manager", activeNav: "menu", outputName: "MenuManagementScreen" },
  PickupSlotsManagement: { role: "manager", activeNav: "slots", outputName: "SlotManagementScreen" },
  ManagerAnalytics: { role: "manager", activeNav: "dashboard", outputName: "AnalyticsScreen" },
  EarningsLedger: { role: "manager", activeNav: "ledger", outputName: "LedgerScreen" },
  OutletSetup: { role: "manager", activeNav: "menu", outputName: "OutletSetupScreen" },
  CampusAdminDashboard: { role: "admin", outputName: "AdminDashboard" },
  OutletApplicationsReview: { role: "admin", outputName: "OutletAppsScreen" },
  OutletManagement: { role: "admin", outputName: "OutletManagementScreen" },
  PenaltyManagement: { role: "admin", outputName: "PenaltyManagementScreen" },
  SuperAdminDashboard: { role: "superadmin", outputName: "SuperAdminDashboard" },
  CampusDetailSuperAdmin: { role: "superadmin", outputName: "CampusDetailScreen" },
  CampusAdminApplication: { role: "auth", outputName: "ApplyAdminScreen" },
  ApplyAsOutletManager: { role: "auth", outputName: "ApplyOutletScreen" },
  StudentHome: { role: "student", outputName: "HomeScreen" },
};

const REACT_ATTRIBUTES = {
  viewbox: "viewBox",
  "stroke-width": "strokeWidth",
  "stroke-linecap": "strokeLinecap",
  "stroke-linejoin": "strokeLinejoin",
  "fill-rule": "fillRule",
  "clip-rule": "clipRule",
  maxlength: "maxLength",
  tabindex: "tabIndex",
  readonly: "readOnly",
  autocomplete: "autoComplete",
  autofocus: "autoFocus",
  for: "htmlFor",
  colspan: "colSpan",
  rowspan: "rowSpan",
};

function camelCase(property) {
  return property.replace(/-([a-z])/g, (_, letter) => letter.toUpperCase());
}

function convertStyle(style) {
  const declarations = style
    .split(";")
    .map((entry) => entry.trim())
    .filter(Boolean)
    .map((entry) => {
      const separator = entry.indexOf(":");
      const property = camelCase(entry.slice(0, separator).trim());
      const value = entry.slice(separator + 1).trim().replace(/\\/g, "\\\\").replace(/"/g, '\\"');
      return `${property}: "${value}"`;
    });

  return `style={{ ${declarations.join(", ")} }}`;
}

function convertHtml(html, config) {
  const bodyMatch = html.match(/<body[^>]*>([\s\S]*?)<\/body>/i);
  let jsx = bodyMatch ? bodyMatch[1].trim() : html;

  jsx = jsx.replace(/<script[\s\S]*?<\/script>/gi, "");
  jsx = jsx.replace(/<nav class="fixed bottom-0[\s\S]*?<\/nav>/i,
    config.role === "manager" ? `<ManagerBottomNav active="${config.activeNav}" />` : "");
  jsx = jsx.replace(/<!--([\s\S]*?)-->/g, (_, comment) => `{/*${comment.trim()}*/}`);
  jsx = jsx.replace(/\bclass=/g, "className=");
  jsx = jsx.replace(/\bstyle="([^"]*)"/g, (_, style) => convertStyle(style));
  jsx = jsx.replace(/\s(onchange|oninput|onsubmit|onmouseover|onmouseout|ontouchstart|ontouchend)="[^"]*"/gi, "");

  for (const [htmlAttribute, reactAttribute] of Object.entries(REACT_ATTRIBUTES)) {
    jsx = jsx.replace(new RegExp(`\\b${htmlAttribute}=`, "gi"), `${reactAttribute}=`);
  }

  jsx = jsx.replace(/\bonclick="toggleAI\(\)"/g, "onClick={toggleAI}");
  jsx = jsx.replace(
    /\bonclick="toggleBottomSheet\(true\)"/g,
    "onClick={() => setSheetOpen(true)}",
  );
  jsx = jsx.replace(
    /\bonclick="toggleBottomSheet\(false\)"/g,
    "onClick={() => setSheetOpen(false)}",
  );
  jsx = jsx.replace(
    /\bonclick="toggleHistory\(\)"/g,
    "onClick={() => setHistoryOpen((open) => !open)}",
  );

  jsx = jsx.replace(
    'className="mt-4 space-y-4" id="ai-content"',
    'className={`${aiOpen ? "mt-4 space-y-4" : "hidden"}`} id="ai-content"',
  );
  jsx = jsx.replace(
    'className="material-symbols-outlined text-muted-text transition-transform" id="ai-toggle-icon"',
    'className={`material-symbols-outlined text-muted-text transition-transform ${aiOpen ? "rotate-0" : "rotate-180"}`} id="ai-toggle-icon"',
  );
  jsx = jsx.replace(
    'className="fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] hidden transition-opacity" id="bottom-sheet-overlay"',
    'className={`fixed inset-0 bg-black/60 backdrop-blur-sm z-[60] transition-opacity ${sheetOpen ? "block" : "hidden"}`} id="bottom-sheet-overlay"',
  );
  jsx = jsx.replace(
    'className="fixed bottom-0 left-0 right-0 z-[70] bg-surface rounded-t-[32px] bottom-sheet-transition translate-y-full px-margin-mobile pt-4 pb-8 max-h-[795px] overflow-y-auto custom-scrollbar border-t border-glow" id="bottom-sheet"',
    'className={`fixed bottom-0 left-0 right-0 z-[70] bg-surface rounded-t-[32px] bottom-sheet-transition px-margin-mobile pt-4 pb-8 max-h-[795px] overflow-y-auto custom-scrollbar border-t border-glow ${sheetOpen ? "translate-y-0" : "translate-y-full"}`} id="bottom-sheet"',
  );
  jsx = jsx.replace(
    'className="hidden overflow-hidden transition-all duration-300" id="history-content"',
    'className={`${historyOpen ? "block" : "hidden"} overflow-hidden transition-all duration-300`} id="history-content"',
  );
  jsx = jsx.replace(
    'className="material-symbols-outlined transition-transform duration-300" id="history-arrow"',
    'className={`material-symbols-outlined transition-transform duration-300 ${historyOpen ? "rotate-180" : "rotate-0"}`} id="history-arrow"',
  );
  jsx = jsx.replace(
    '<form className="space-y-stack-lg">',
    '<form className="space-y-stack-lg" onSubmit={(event) => event.preventDefault()}>',
  );
  jsx = jsx.replace(/<form(?![^>]*onSubmit)([^>]*)>/g, '<form$1 onSubmit={(event) => event.preventDefault()}>');

  return jsx;
}

function componentSource(name, config, jsx) {
  const hooks = [];
  const setup = [];

  if (name === "ManagerDashboard") {
    hooks.push("useState");
    setup.push("  const [aiOpen, setAiOpen] = useState(true);");
    setup.push("  const toggleAI = () => setAiOpen((open) => !open);");
  }
  if (name === "MenuManagement") {
    hooks.push("useState");
    setup.push("  const [sheetOpen, setSheetOpen] = useState(false);");
  }
  if (name === "PickupSlotsManagement") {
    hooks.push("useState");
    setup.push("  const [historyOpen, setHistoryOpen] = useState(false);");
  }

  const reactImport = hooks.length
    ? `import { ${[...new Set(hooks)].join(", ")} } from "react";\n`
    : "";

  const navImport = jsx.includes("<ManagerBottomNav")
    ? 'import ManagerBottomNav from "../../components/layout/ManagerBottomNav";\n'
    : "";

  return `${reactImport}${navImport}

/**
 * Generated from the Google Stitch screen export.
 * Source: frontend/tmp/stitch_screens/${name}.html
 */
export default function ${config.outputName}() {
${setup.length ? `${setup.join("\n")}\n` : ""}  return (
    <div className="${config.role}-screen">
${jsx
  .split("\n")
  .map((line) => `      ${line}`)
  .join("\n")}
    </div>
  );
}
`;
}

for (const [name, config] of Object.entries(SCREENS)) {
  const inputPath = path.join(INPUT_DIR, `${name}.html`);
  const outputDir = path.resolve(__dirname, `../src/pages/${config.role}`);
  fs.mkdirSync(outputDir, { recursive: true });
  const outputPath = path.join(outputDir, `${config.outputName}.jsx`);
  const html = fs.readFileSync(inputPath, "utf8");
  const jsx = convertHtml(html, config);
  fs.writeFileSync(outputPath, componentSource(name, config, jsx), "utf8");
  console.log(`Generated ${path.relative(process.cwd(), outputPath)}`);
}
