type Script = {id: string};
type Route<S extends Script> = {id: string; label: string; lineCount: number; scripts: S[]};
export function readerCategoryId(id: string): string;
export function readerCategories<S extends Script, R extends Route<S>>(routes: R[]): (Omit<R, 'scripts'> & {scripts: (S & {routeId: string; imageOnly: boolean})[]})[];
