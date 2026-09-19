import tseslint from "typescript-eslint";
import roblox from "eslint-plugin-roblox-ts";
import prettier from "eslint-config-prettier";

export default tseslint.config(
	{ ignores: ["out/**", "include/**", "node_modules/**", "scripts/**", "eslint.config.mjs"] },
	...tseslint.configs.recommended,
	roblox.configs.recommended,
	prettier,
	{
		languageOptions: {
			parserOptions: {
				projectService: true,
				tsconfigRootDir: import.meta.dirname,
			},
		},
		rules: {
			// The template deliberately ships empty, growing interfaces
			// (network event maps, component attribute maps).
			"@typescript-eslint/no-empty-object-type": "off",
		},
	},
);
