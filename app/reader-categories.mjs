export const readerCategoryId = id => id;

export function readerCategories(routes) {
  return routes
    .filter(route => route.id !== 'system')
    .map(route => ({
      ...route,
      scripts: route.scripts.map(script => ({...script, routeId: route.id, imageOnly: false})),
    }));
}
