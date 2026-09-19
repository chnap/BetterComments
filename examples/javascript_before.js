const endpoint = "https://example.com/api";
const marker = "hello // world";

/*
 * Iterate over every item returned by the API.
 * Check whether the item is currently active.
 * Add active items to the result array.
 */
const activeItems = items.filter(isActive);

// eslint-disable-next-line no-console
console.log(activeItems);

