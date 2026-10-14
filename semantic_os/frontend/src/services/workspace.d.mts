export function workspaceReads(page: string): string[];
export function inboxToolNames(descriptors: {name:string}[], allowedTools: string[]): string[];
export function messageSpeaker(message: {direction:string;metadata?:{kind?:string}}): string;
