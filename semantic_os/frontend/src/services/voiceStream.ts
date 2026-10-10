import { request, mediaUrl } from './api';
export async function connectVoice(callId: string, receive: (event: any) => void): Promise<WebSocket> {
  const { ticket } = await request('/api/calls/' + callId + '/stream-ticket', 'POST', { confirmed: true });
  const socket = new WebSocket(mediaUrl);
  socket.onopen = () => socket.send(JSON.stringify({ event: 'start', ticket }));
  socket.onmessage = message => { try { receive(JSON.parse(message.data)); } catch { receive({ event: 'error', code: 'invalid_input' }); } };
  socket.onerror = () => receive({ event: 'error', code: 'provider_error' });
  return socket;
}
export function sendSyntheticAudio(socket: WebSocket, text: string, sequence: number): void {
  const bytes = new TextEncoder().encode(text);
  const payload = btoa(String.fromCharCode(...bytes));
  socket.send(JSON.stringify({ event: 'media', frame: { sequence, utterance_id: crypto.randomUUID(),
    payload, encoding: 'fixture_utf8', sample_rate: 8000, final: true } }));
}
