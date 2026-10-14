/** Ordered profile writes; discard queued writes after changing tenant. */
export function languageSaver(write,isCurrent,report) {
  let tail=Promise.resolve();
  return (context,locale)=>{
    tail=tail.then(async()=>{if(!isCurrent(context))return;
      try{await write(locale);if(isCurrent(context))report(null);}
      catch{if(isCurrent(context))report('localeSyncFailed');}
    });return tail;
  };
}
export function reconciledLocale(profile,current,changedSinceRequest) {
  if(changedSinceRequest)return current;
  return ['bg-BG','en-US'].includes(profile?.ui_locale)?profile.ui_locale:current;
}
