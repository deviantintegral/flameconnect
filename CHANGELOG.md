# Changelog

## [0.2.0](https://github.com/deviantintegral/flameconnect/compare/v0.1.0...v0.2.0) (2026-02-26)


### Features

* add heat-status CLI set command for TUI parity ([d442140](https://github.com/deviantintegral/flameconnect/commit/d44214033f5ad0c9be9f8765559c8d142178a988))


### Bug Fixes

* align public API and docs with project philosophy ([df4a6e6](https://github.com/deviantintegral/flameconnect/commit/df4a6e6846509fc19ab17f79e5c5fe6ba34d510b))
* **ci:** limit mutmut parallelism to prevent OOM in CI ([2bdb46b](https://github.com/deviantintegral/flameconnect/commit/2bdb46b91a3acb430c5dc0c7661834190d7054a7))


### Documentation

* add initial AGENTS.md ([#29](https://github.com/deviantintegral/flameconnect/issues/29)) ([f008f5b](https://github.com/deviantintegral/flameconnect/commit/f008f5b7cb9cab9d86edf30c8943992b7824cad6))
* clarify how mutmut copies files ([0daf94b](https://github.com/deviantintegral/flameconnect/commit/0daf94b25030bfefb1fc947309227725417a38ee))
* more 🔥 ([9de07d6](https://github.com/deviantintegral/flameconnect/commit/9de07d600ef9673952dca4d3d6ae0944594b9f04))
* update README with API versioning information ([0299759](https://github.com/deviantintegral/flameconnect/commit/029975913dfa9e170b23eaa4d42582f6a3d1dc4b))
* update README with complete CLI set parameters and TUI keybindings ([81ed9c7](https://github.com/deviantintegral/flameconnect/commit/81ed9c7f3ab27664a1d1b929cf9f77d8e6e18bdf))

## 0.1.0 (2026-02-26)


### Features

* add async API client with typed fireplace control ([027e912](https://github.com/deviantintegral/flameconnect/commit/027e9128c9cd139ec9ae322de6027b9712d255c9))
* add CI/CD workflows and project README ([a63fa02](https://github.com/deviantintegral/flameconnect/commit/a63fa021d398148ce341e7447de43463e7e977f3))
* add CLI set commands and TUI keybindings for fireplace controls ([076c8e7](https://github.com/deviantintegral/flameconnect/commit/076c8e763da40d6347d39df3116a695f0bd2f948))
* add CLI, TUI dashboard, and comprehensive test suite ([3d41d83](https://github.com/deviantintegral/flameconnect/commit/3d41d83dfcf2fecacf3044377483c0db66051af1))
* add client-side temperature C/F conversion ([f6261fb](https://github.com/deviantintegral/flameconnect/commit/f6261fbae6b8468a299db74ce198290a53239f69))
* add deliver_screenshot override to create Downloads directory ([21dc540](https://github.com/deviantintegral/flameconnect/commit/21dc5408571fba0e297a733c3a617d0c863d7f9d))
* add direct B2C credential login with browser fallback ([59aae6a](https://github.com/deviantintegral/flameconnect/commit/59aae6a51c3105f15bc9174dac6031d739611f80))
* add fireplace control via WriteWifiParameters API ([ceb99e9](https://github.com/deviantintegral/flameconnect/commit/ceb99e9f1b80617971a76eebd4cb73e9d1abbb93))
* add fireplace controls to command palette ([80035ab](https://github.com/deviantintegral/flameconnect/commit/80035ab0d4c787469868d5b6df91f9c143d50abd))
* add fireplace status section with ASCII art and side-by-side layout ([7a02769](https://github.com/deviantintegral/flameconnect/commit/7a027693aa47c2e607d8fde1e130f0c82c4954fc))
* add heat mode selection dialog, fireplace switcher, and CLI boost syntax ([3c7c7cd](https://github.com/deviantintegral/flameconnect/commit/3c7c7cde6236c5a7ebdba79772001cef6a339ece))
* add heat on/off toggle (key 's') ([fee5d1c](https://github.com/deviantintegral/flameconnect/commit/fee5d1ca45355ff4c33c4328d57c8f4754cddf94))
* add masked password input that shows * per character ([13cca22](https://github.com/deviantintegral/flameconnect/commit/13cca22bf18e2030e883c11976f287a855243eba))
* add mutmut config and expand CI mutation testing to 4 modules ([4b35e68](https://github.com/deviantintegral/flameconnect/commit/4b35e6832cdd52a6282c7515ff669daac4d8e040))
* add NAMED_COLORS, CLI set commands, and TUI dialog screens ([0ba8c7e](https://github.com/deviantintegral/flameconnect/commit/0ba8c7e982f2cdd7386658d61c0ae0549be7c863))
* add pytest-cov and wire code coverage into tests and CI ([fca4c04](https://github.com/deviantintegral/flameconnect/commit/fca4c04ae9ef39d557ebe3ba74a5739254c7b6aa))
* add responsive layout for 80x24 terminal support ([e73246b](https://github.com/deviantintegral/flameconnect/commit/e73246b1f922bc5ea587dc80b3d9803abfc98f45))
* add reusable RGBW colour picker dialog (ColorScreen) ([cdd8690](https://github.com/deviantintegral/flameconnect/commit/cdd8690490850571cf8d6cf640fa396485c2dd51))
* add TUI keybindings and actions for all flame effect controls ([fb0a402](https://github.com/deviantintegral/flameconnect/commit/fb0a402a7a2611605ddc0ced085dc44ca8f08c27))
* add TUI messages panel with log capture, respect -v flag, fix screen cleanup ([fb28e77](https://github.com/deviantintegral/flameconnect/commit/fb28e775fe5328fe422c20b2f6a66a90004e81da))
* add typed models, enums, constants, and exception hierarchy ([9e45a77](https://github.com/deviantintegral/flameconnect/commit/9e45a779eb1660da300fd378e638159482b932aa))
* add wire protocol codec and async auth module ([c155d8b](https://github.com/deviantintegral/flameconnect/commit/c155d8bd6f4d0cf9df8dc32ea38d62d6beaa1251))
* auth and read fireplace data ([58eea0c](https://github.com/deviantintegral/flameconnect/commit/58eea0c17ab7673cb5a8b02cf7c68cb9b88d44a6))
* automatically wrap text ([3b88145](https://github.com/deviantintegral/flameconnect/commit/3b88145185e5ba62480b3502ebdd45b2dafd7c40))
* clickable parameter fields and temperature adjustment dialog ([dadc6f7](https://github.com/deviantintegral/flameconnect/commit/dadc6f78d8b8c2976aada9bfde8424150300df60))
* clickable values, git hash header, fireplace visual refinements ([00e176c](https://github.com/deviantintegral/flameconnect/commit/00e176c45477d92b7a7c3b4735c70f1cc6770020))
* display on instead of manual ([4396b65](https://github.com/deviantintegral/flameconnect/commit/4396b65e0d45f24394742d95b6e75f06331bd1bc))
* dynamically size fireplace art to fill widget width ([a4525f6](https://github.com/deviantintegral/flameconnect/commit/a4525f6001273c8410f5b1e08f7676d0e4ed32d8))
* initialize project scaffolding with uv and tooling configuration ([0239675](https://github.com/deviantintegral/flameconnect/commit/0239675761828acfc917393fe26fb0764b6206ea))
* launch TUI by default when no subcommand is given ([de68838](https://github.com/deviantintegral/flameconnect/commit/de688384ee3d693ea475d00c58499c15fdd23d7b))
* log changed parameter attributes on refresh in TUI messages panel ([895afdd](https://github.com/deviantintegral/flameconnect/commit/895afdd28e25d1fadecedd3714527b36e1a5f638))
* overhaul TUI widgets with display name helper, boost fix, ASCII art, and case standardisation ([ccc86eb](https://github.com/deviantintegral/flameconnect/commit/ccc86eb116d02736977a9db37f659a9e5ec0a536))
* prompt user for timer duration instead of hardcoding 60 minutes ([6c9b3bb](https://github.com/deviantintegral/flameconnect/commit/6c9b3bb05d840bcf6b29298d5f9a4a68d2bad8f1))
* replace flame speed cycling with selection dialog ([24517fd](https://github.com/deviantintegral/flameconnect/commit/24517fdde3d1a9d00037f8d959da497e4d285e86))
* replace raw terminal auth prompt with Textual modal dialog ([8b5a086](https://github.com/deviantintegral/flameconnect/commit/8b5a08656694bd8d7d570ba495defce4afb47a65))
* restructure TUI layout with info bar, help panel, and simplified footer ([e21516e](https://github.com/deviantintegral/flameconnect/commit/e21516eadf7962e6af182e9bc1d7e4e85e125998))
* rewrite FireplaceVisual with state-driven ASCII art ([9041d7d](https://github.com/deviantintegral/flameconnect/commit/9041d7df2e637a996e7bf6cfeb060a46429da4ed))
* show estimated turn-off time when timer is enabled ([a0928b4](https://github.com/deviantintegral/flameconnect/commit/a0928b4736fa33a59112d72faf500fa4d30bdcbd))
* split brightness byte into brightness and pulsating effect fields ([1f3ce71](https://github.com/deviantintegral/flameconnect/commit/1f3ce715f5df0ed24187df2706924f0127e3c7cf))
* TUI fixes — border, version, help toggle, labels, dialogs, flame animation, heat visual, media diagnostics ([c517ac0](https://github.com/deviantintegral/flameconnect/commit/c517ac0a0a01c63d315dc099dc99ef4ffc30ba2b))
* wire dashboard state to visual and add rendering tests ([aec1e57](https://github.com/deviantintegral/flameconnect/commit/aec1e5741f748bb9ee189e30e0a9bebc6c4ea8bf))


### Bug Fixes

* **ci:** add environment declaration for release-please secret access ([#27](https://github.com/deviantintegral/flameconnect/issues/27)) ([3138bf8](https://github.com/deviantintegral/flameconnect/commit/3138bf8babd1e0b2b199b056da952504caf0ac1a))
* **ci:** ensure CI checks run on release-please PRs ([#26](https://github.com/deviantintegral/flameconnect/issues/26)) ([6de3492](https://github.com/deviantintegral/flameconnect/commit/6de3492692788ada76938ac4b09a53187e2e4588))
* correct heat mode writes by fixing encoder payload size and modal callback timing ([62d6420](https://github.com/deviantintegral/flameconnect/commit/62d642046ef130ee92f4f6d0cd30c0f3db089018))
* correct off-by-one in boost duration decode/encode ([72c8060](https://github.com/deviantintegral/flameconnect/commit/72c806058064dc7c3903b74d693729f2a4a4317d))
* decode base64 wire protocol for parameter reading ([92a72af](https://github.com/deviantintegral/flameconnect/commit/92a72affad2ad5ac3fdec37032852094fda7b3b9))
* enforce explicit display order for parameters in TUI ([3d940e8](https://github.com/deviantintegral/flameconnect/commit/3d940e8dae02bf9de57501a9b6f461addc0fe9d0))
* flame effect graphic, click actions, and duplicate light labels ([54486db](https://github.com/deviantintegral/flameconnect/commit/54486db8b45626e722bc85f4b8fc617c6074f1f7))
* handle missing fields in GetFireOverview response ([719c2d2](https://github.com/deviantintegral/flameconnect/commit/719c2d2feb2fb11c8befca69f55ed0679e5a9e52))
* handle variable-length HeatSettings parameter and improve decode error logging ([c430cb5](https://github.com/deviantintegral/flameconnect/commit/c430cb5235ae44dd197783f3b58548d6535f9eb1))
* hide duplicate command palette entry from left side of footer ([5c27178](https://github.com/deviantintegral/flameconnect/commit/5c27178170a4108a5da98dac54bf2e859a014a1b))
* improve parameter display order and error text clarity ([66770bd](https://github.com/deviantintegral/flameconnect/commit/66770bd61f16517e4b4afa16f4ad78b4cef49460))
* improve refresh log messages in TUI ([92a1008](https://github.com/deviantintegral/flameconnect/commit/92a10084b2f12da4cf3081aa5e452053fd21cf23))
* match ALL flame color palette to real fireplace (yellow/orange/blue) ([0f42380](https://github.com/deviantintegral/flameconnect/commit/0f423802c3f63734eab95ada9953a1e62d79444f))
* match fireplace panel height to info panel ([a77304f](https://github.com/deviantintegral/flameconnect/commit/a77304fe6cfd87119f766ab40162bc1cc34a64b2))
* preserve current temperature when changing fireplace mode ([76bb7ee](https://github.com/deviantintegral/flameconnect/commit/76bb7eef1bc5a07d4e6c41a8c5991604267c8bb9))
* prevent Rich markup escape in fireplace ASCII art ([3c7d760](https://github.com/deviantintegral/flameconnect/commit/3c7d76076c177ff86b4247e75226adbb24aea2e6))
* remove API polling interval, show last-updated timestamp in header ([4a00219](https://github.com/deviantintegral/flameconnect/commit/4a0021977199a9b064a41d114e1c50629bec95cb))
* remove connection state from header (API always returns Unknown) ([edaf934](https://github.com/deviantintegral/flameconnect/commit/edaf934215298dd51e73c7f1fbf92bb422376eae))
* reorder flame effect options for consistent UI grouping ([14b0c6d](https://github.com/deviantintegral/flameconnect/commit/14b0c6dbfd47418dfb1f6603753efdf9df0cc4a4))
* revert brightness from enum to int, use display-only name mapping ([ba2ed82](https://github.com/deviantintegral/flameconnect/commit/ba2ed82e2a7b50ccc837f5e9d74205e91d4ab83c))
* rewire overhead light to use light_status (byte 18) ([dcc9334](https://github.com/deviantintegral/flameconnect/commit/dcc93346d41a6656e7f30435587fde96ea2f5c38))
* show ^p key hint for command palette and display fireplace info in header ([75476d9](https://github.com/deviantintegral/flameconnect/commit/75476d95913279baf8a83d8b8b1e17429fe31a1f))
* show dark gray LED and media bed when fireplace is off ([12340b5](https://github.com/deviantintegral/flameconnect/commit/12340b5a66f2dbe47535d3c6e04ea18138c66190))
* show immediate feedback before API calls in all actions ([68d83fc](https://github.com/deviantintegral/flameconnect/commit/68d83fcb0491245d38e6d394e3764c6baa8d620f))
* use direct widget manipulation for compact layout ([923875c](https://github.com/deviantintegral/flameconnect/commit/923875c88db5c78a17c8b0b82a67840b9fccc68b))
* use DummyCookieJar to prevent quoted cookie re-injection ([3001e3e](https://github.com/deviantintegral/flameconnect/commit/3001e3e55d372dccf604ab8af7599f3243557878))
* use friendly_name from fire list API for header display ([b14b772](https://github.com/deviantintegral/flameconnect/commit/b14b7729d28b834171ab665fad7db808108438b2))
* use per-widget CSS classes for compact layout ([e15ecc3](https://github.com/deviantintegral/flameconnect/commit/e15ecc33fac8f0cfa8a4236ee55e9778c26d2e21))
* use run_worker for all commands so feedback renders immediately ([7e9d6ce](https://github.com/deviantintegral/flameconnect/commit/7e9d6ce3071a31a0680377a6c87579698d5f467f))
* use terminfo for terminal cleanup instead of hardcoded xterm codes ([e6bcb50](https://github.com/deviantintegral/flameconnect/commit/e6bcb5015a9bcdd44886a201f60f21336b423d2a))
* width of field labels ([817ec38](https://github.com/deviantintegral/flameconnect/commit/817ec38ea7084c0238789e2bfbc9761c6f6c31bf))
* workflow badge and clone URL in README ([#19](https://github.com/deviantintegral/flameconnect/issues/19)) ([e20ff49](https://github.com/deviantintegral/flameconnect/commit/e20ff498b1ba35ecd36bb3f7bae485c7a1e2acb0))
* write terminal cleanup to stderr to match Textual's driver ([e310589](https://github.com/deviantintegral/flameconnect/commit/e310589ad907b8f513ae624895b330d82b3484d4))


### Documentation

* add execution blueprint and task files for plan 12 ([b510d12](https://github.com/deviantintegral/flameconnect/commit/b510d128ade40e55d800b8cc8508985ac2ec0155))
* add plan 02 for fireplace state controls (CLI & TUI) ([fea33d6](https://github.com/deviantintegral/flameconnect/commit/fea33d628a8bf5a4576874086fe2da04ad0be04c))
* add plan 04 for TUI visual polish and layout restructuring ([5ce695d](https://github.com/deviantintegral/flameconnect/commit/5ce695d3f31453c6b4d63e27788c6a2e0d0bbea1))
* add report from app analysis ([c387d3d](https://github.com/deviantintegral/flameconnect/commit/c387d3de3bfd06ca057218922431d33442ee3197))
* add screenshot of the tui ([#20](https://github.com/deviantintegral/flameconnect/issues/20)) ([f5b714a](https://github.com/deviantintegral/flameconnect/commit/f5b714afd712f801c102c0d3785fb10b1d25487e))
* add tasks and live API testing policy ([c657406](https://github.com/deviantintegral/flameconnect/commit/c657406b3ec072f98e7a12d885ef63d4b9e0667d))
* archive execute tui plan ([bd32351](https://github.com/deviantintegral/flameconnect/commit/bd32351477b483421de4ef015242c7283bd1bda1))
* archive flame effect plan ([113f060](https://github.com/deviantintegral/flameconnect/commit/113f0605bdfff9f221da3fc521d16c11b9824731))
* archive plan 09 (tui bug fixes) ([c038ba5](https://github.com/deviantintegral/flameconnect/commit/c038ba5fc0606e110492c33a497f537c38afc56d))
* archive plan 10 (pytest-cov integration) ([95e140c](https://github.com/deviantintegral/flameconnect/commit/95e140c78bfe9f489ecbb16a493f6afe43b67673))
* archive plan 11 (increase test coverage) ([420322e](https://github.com/deviantintegral/flameconnect/commit/420322e0a0cc6d440b62f85e34b442dd2d111c5d))
* archive plans ([1f7977f](https://github.com/deviantintegral/flameconnect/commit/1f7977f1e433cd4378c9ee669324c797f9a9fab2))
* archive tui refinements ([64d4e31](https://github.com/deviantintegral/flameconnect/commit/64d4e31b1a5b0b58e31c494c37fcafd308d6bb6f))
* create plan 12 (mutation testing expansion) ([b811411](https://github.com/deviantintegral/flameconnect/commit/b811411dc8b50354fb1133826eb5ec3ba5ddb063))
* fill in more choices ([c7c6027](https://github.com/deviantintegral/flameconnect/commit/c7c60274cc041f75f883213f3d701dba80102ae3))
* initial ai task manager setup ([fe0ca39](https://github.com/deviantintegral/flameconnect/commit/fe0ca3928cba5a5958f8b86b34a2da5f29b7c753))
* initial foundation doc ([07fbf12](https://github.com/deviantintegral/flameconnect/commit/07fbf12e62fa325ac78f8b789226de8e7cdcfb70))
* remove pip install references, replace with uv ([#24](https://github.com/deviantintegral/flameconnect/issues/24)) ([bcf2bd0](https://github.com/deviantintegral/flameconnect/commit/bcf2bd07011c96553d4a4c9234c1b9c8a702789e))
* section on API usage for backend owners ([#25](https://github.com/deviantintegral/flameconnect/issues/25)) ([6ca765e](https://github.com/deviantintegral/flameconnect/commit/6ca765e31ff037c3eb7ba55c5e385feb5cf7a487))
