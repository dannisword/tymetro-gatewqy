import { defineStore } from "pinia";
export type Lang = { locale: string; values: Record<string, string> };

export const useLocaleStore = defineStore("useLocaleStore", {
  state: () => ({
    langs: [] as Lang[],
    missingKeys: new Map<string, Set<string>>(), // key: locale → Set(keys)
  }),
  getters: {
    // 合併後的字典（同 locale 多筆依序覆蓋）
    dict: (x) => (locale: string) =>
      x.langs
        .filter((l) => l.locale === locale)
        .reduce(
          (acc, cur) => Object.assign(acc, cur.values),
          {} as Record<string, string>
        ),
  },
  actions: {
    async setLocale(entry: Lang) {
      // 1) 找到既有的同 locale
      const idx = this.langs.findIndex((x) => x.locale === entry.locale);

      // 2) 覆蓋
      if (idx >= 0) {
        this.langs.splice(idx, 1, entry);
      } else {
        this.langs.push(entry);
      }
    },
    addMissing(locale: string, key: string) {
      const set = this.missingKeys.get(locale) ?? new Set<string>();
      set.add(key);
      this.missingKeys.set(locale, set);
    },
    clearMissing(locale?: string) {
      if (locale) this.missingKeys.delete(locale);
      else this.missingKeys.clear();
    },
  },
});
