export function languageSaver(write:(locale:string)=>Promise<unknown>,isCurrent:(context:string)=>boolean,report:(code:string|null)=>void):(context:string,locale:string)=>Promise<void>;
export function reconciledLocale(profile:{ui_locale?:string},current:string,changedSinceRequest:boolean):string;
