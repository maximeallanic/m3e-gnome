// Shell surfaces captured by the style bench: one per element of the spec, grouped by concern in the sibling
// modules. Each module exports a table of surfaces (shape documented in common.js); this index merges them.
import {APP_GRID_SURFACES} from './app-grid.js';
import {BAR_SURFACES} from './bar.js';
import {CALENDAR_SURFACES} from './calendar.js';
import {DIALOG_SURFACES} from './dialogs.js';
import {KEYBOARD_SURFACES} from './keyboard.js';
import {LOCK_SURFACES} from './lock.js';
import {LOGIN_SURFACES} from './login.js';
import {MENU_SURFACES} from './menus.js';
import {NOTIFICATION_SURFACES} from './notifications.js';
import {OSD_SURFACES} from './osd.js';
import {SCREENSHOT_SURFACES} from './screenshot-ui.js';
import {SEARCH_SURFACES} from './search.js';
import {SETTINGS_SURFACES} from './quick-settings.js';
import {WINDOW_SURFACES} from './windows.js';

export const SURFACES = {
    ...BAR_SURFACES,
    ...MENU_SURFACES,
    ...SETTINGS_SURFACES,
    ...CALENDAR_SURFACES,
    ...NOTIFICATION_SURFACES,
    ...SEARCH_SURFACES,
    ...APP_GRID_SURFACES,
    ...WINDOW_SURFACES,
    ...DIALOG_SURFACES,
    ...OSD_SURFACES,
    ...SCREENSHOT_SURFACES,
    ...KEYBOARD_SURFACES,
    ...LOCK_SURFACES,
    ...LOGIN_SURFACES,
};
