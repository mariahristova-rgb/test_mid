const required = ["VITE_AUTH0_DOMAIN", "VITE_AUTH0_CLIENT_ID", "VITE_AUTH0_AUDIENCE"];
const missing = required.filter((key) => !String(process.env[key] || "").trim());

if (missing.length) {
  console.error(`Frontend image build refused: missing required identity build args: ${missing.join(", ")}`);
  process.exit(1);
}

if (/(^|\.)auth0\.com$/i.test(process.env.VITE_AUTH0_DOMAIN)) {
  console.error("Frontend image build refused: production identity must use an approved custom Auth0 domain.");
  process.exit(1);
}
