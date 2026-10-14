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
export function inboxToolNames(descriptors, allowedTools) {
  const supported = ['CheckAvailability','CreateAppointment','RescheduleAppointment','CancelAppointment','SendMessage','CreateFollowUpTask','EscalateToHuman'];
  return descriptors.map(item=>item.name).filter(name=>supported.includes(name) && allowedTools.includes(name));
}
export function messageSpeaker(message) {
  if(message.direction==='inbound')return 'user';
  return message.metadata?.kind==='human'?'human':'assistant';
}
