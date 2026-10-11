// Existing URLs are retained; this groups presentation without granting access.
export const navigationGroups = [
  { key: 'businessWorkspace', pages: ['dashboard', 'inbox', 'appointments', 'assistants'] },
  { key: 'assistantStudio', pages: ['setup', 'testing', 'widgets', 'agents', 'channels'] },
  { key: 'operationsWorkspace', pages: ['operations', 'calls', 'integrations', 'google', 'onboarding', 'billing', 'usage', 'settings', 'administration'] },
];
export function permittedGroups(role, platformAdmin = false) {
  const operator = ['admin', 'operator'].includes(role);
  const adminPages = ['setup', 'widgets', 'google', 'onboarding', 'billing', 'settings', 'agents', 'channels', 'integrations'];
  return navigationGroups.map(group => ({...group, pages: group.pages.filter(page =>
    page === 'administration' ? platformAdmin : adminPages.includes(page) ? role === 'admin' :
      ['testing', 'operations', 'calls', 'usage'].includes(page) ? operator : Boolean(role))
  })).filter(group => group.pages.length);
}
