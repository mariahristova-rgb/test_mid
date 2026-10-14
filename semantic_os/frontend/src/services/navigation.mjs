// Existing URLs are retained; this groups presentation without granting access.
export const navigationGroups = [
  { key: 'businessWorkspace', pages: ['dashboard', 'assistants', 'inbox', 'appointments', 'leads', 'channels', 'analytics', 'usage', 'billing', 'team', 'settings'] },
  { key: 'assistantStudio', pages: ['progress', 'setup', 'testing', 'widgets', 'health', 'quality'] },
  { key: 'operationsWorkspace', pages: ['operations', 'calls', 'integrations', 'google', 'onboarding', 'agents', 'administration'] },
];
export function permittedGroups(role, platformAdmin = false) {
  const operator = ['admin', 'operator'].includes(role);
  const adminPages = ['team','progress','setup', 'widgets', 'google', 'onboarding', 'billing', 'settings', 'agents', 'channels', 'integrations'];
  return navigationGroups.map(group => ({...group, pages: group.pages.filter(page =>
    page === 'administration' ? platformAdmin : adminPages.includes(page) ? role === 'admin' :
      ['quality','testing', 'operations', 'calls', 'usage'].includes(page) ? operator : Boolean(role))
  })).filter(group => group.pages.length);
}
