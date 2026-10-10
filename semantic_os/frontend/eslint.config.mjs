import vue from "eslint-plugin-vue";
import typescriptParser from "@typescript-eslint/parser";

export default [
  ...vue.configs["flat/recommended"],
  {
    files: ["**/*.ts"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parser: typescriptParser,
    },
  },
  {
    files: ["**/*.{ts,vue}"],
    languageOptions: {
      ecmaVersion: "latest",
      sourceType: "module",
      parserOptions: {
        parser: typescriptParser,
        extraFileExtensions: [".vue"],
      },
    },
    rules: {
      "vue/html-indent": "off",
      "vue/max-attributes-per-line": ["warn", { singleline: 5 }],
      "vue/multi-word-component-names": "off",
    },
  },
  {
    ignores: ["dist/", "node_modules/", "*.d.ts", "next-env.d.ts"],
  },
];
