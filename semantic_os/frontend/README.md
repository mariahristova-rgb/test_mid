# Assistant frontend

Vue 3/Vite application. `npm ci --ignore-scripts`, `npm run dev`, `npm test`, `npm run typecheck`, `npm run lint`, `npm run build`.

See the [root README](../../README.md) for backend startup and authentication. All nine screens use Bulgarian/English resources; UI language is separate from conversation/voice language. Credentials stay in memory. External channels and speech are synthetic mocks; screens label this state. Existing Vue/Tailwind conventions and the reusable EmptyState component were retained. `vue-tsc` is a development-only addition for template checking.
