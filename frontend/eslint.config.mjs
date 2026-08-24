import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTypeScript from "eslint-config-next/typescript";

// Next 16 ships native flat configs; the old FlatCompat("next/...") shim crashes on them.
const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTypeScript,
  // Restate eslint-config-next's own defaults, which globalIgnores replaces.
  globalIgnores([".next/**", "out/**", "build/**", "next-env.d.ts"]),
]);

export default eslintConfig;
