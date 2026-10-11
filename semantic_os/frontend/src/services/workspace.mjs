// Route-specific read plans: no unrelated patient/business lists on configuration pages.
export function workspaceReads(page) {
  const pages = {
    dashboard: [], assistants: ['assistants'], agents: ['agents'],
    inbox: ['assistants', 'inbox', 'contacts', 'appointments', 'approvals'],
    calls: ['assistants', 'calls'], appointments: ['appointments', 'follow-up-tasks'],
    channels: ['assistants', 'connections'], integrations: ['assistants', 'connections'], settings: ['contacts'],
  };
  return ['bootstrap', ...(pages[page] || [])];
}
