export const stageTargets:number[];
export function customerStage(step:number):number;
export function adjacentStep(step:number,direction:number):number;
export function parseFaqImport(text:string,currentCount?:number):Record<string,string>[];
