// Search surface: test providers, remote provider guard, overview search results.
import GioUnix from 'gi://GioUnix';
import GLib from 'gi://GLib';
import St from 'gi://St';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';

import {wait, waitUntil} from '../tools.js';
import {TEXT_SIZE, findActor, findAllByClass} from './common.js';
import {closeOverview, openOverview} from './overview.js';

// In-process test search provider (SearchController.addProvider, like an extension): appInfo present -> section
// as a list (ListSearchResults: .search-section-content, .list-search-result), absent -> grid (GridSearchResults:
// .grid-search-result). D-Bus providers of the nested Shell are not guaranteed.
function makeProvider(id, appInfo, results) {
    const ids = results.map(r => r.id);
    return {
        id, appInfo, isRemoteProvider: false, canLaunchSearch: false,
        getInitialResultSet: async () => ids,
        getSubsearchResultSet: async () => ids,
        getResultMetas: async requested => requested.map(i => {
            const r = results.find(x => x.id === i);
            return {id: i, name: r.name, description: r.description ?? '',
                createIcon: size => new St.Icon({icon_name: r.icon, icon_size: size})};
        }),
        filterResults: (res, max) => res.slice(0, max),
        activateResult: () => {},
        launchSearch: () => {},
    };
}

function testAppInfo() {
    const kf = new GLib.KeyFile();
    const data = '[Desktop Entry]\nType=Application\nName=Test documents\nExec=true\nIcon=folder\n';
    kf.load_from_data(data, data.length, GLib.KeyFileFlags.NONE);
    return GioUnix.DesktopAppInfo.new_from_keyfile(kf);
}

// Search providers, set ONCE for the whole life of the (disposable) nested Shell: D-Bus providers (Files,
// Settings...) removed - activated on the private bus, they still search the real home directory (real HOME) and
// their results vary - and test providers added. No removal / restore for each scenario: that back and forth
// (removeProvider destroys the provider's display) stopped the nested Shell without a message at the next
// scenario (seen twice, search:light then previews).
let benchProviders = null;
// D-Bus providers (isRemoteProvider): three layers. (1) nested.sh compiles
// org.gnome.desktop.search-providers disable-external=true into the nested Shell's dconf database (none is
// loaded); (2) removed here, at opening and just before set_text (the Shell reloads them asynchronously when the
// installed apps change: "Files" came back at the 3rd scenario, with file names of the real home directory);
// (3) verifyNoRemote() fails the scenario if one is left after the search.
function removeRemoteProviders() {
    const sc = Main.overview.searchController;
    for (const p of sc._searchResults._providers.filter(x => x.isRemoteProvider))
        sc.removeProvider(p);
}

function verifyNoRemote() {
    const remote = Main.overview.searchController._searchResults._providers.filter(x => x.isRemoteProvider);
    if (remote.length)
        throw new Error(`remote search provider present: ${remote.map(p => p.id).join(', ')}`);
}

// Check of the guard (slow test, M3E_BENCH_STYLE_FAKE_REMOTE=1): fake "remote" provider IN PROCESS (no D-Bus),
// added after the removal like an asynchronous reload would; verifyNoRemote() must fail the scenario. Removed by
// closeSearch().
const FAKE_REMOTE = GLib.getenv('M3E_BENCH_STYLE_FAKE_REMOTE') === '1';

function setProviders() {
    const sc = Main.overview.searchController;
    removeRemoteProviders();
    if (benchProviders)
        return benchProviders;
    const list = makeProvider('m3e-bench-list', testAppInfo(), [
        // Without a description: ListSearchResult links the description label to the result's accessibility
        // (DESCRIBED_BY); relations suspected in the nested Shell stops at the 2nd "search" scenario
        // ("clutter_actor_get_accessible: assertion failed" just before). Description colour: visual review in a
        // session.
        {id: 'l1', name: 'First term', icon: 'text-x-generic-symbolic'},
        {id: 'l2', name: 'Second term', icon: 'text-x-generic-symbolic'},
        {id: 'l3', name: 'Term', icon: 'text-x-generic-symbolic'},
    ]);
    const grid = makeProvider('m3e-bench-grid', null, [
        {id: 'g1', name: 'Term one', icon: 'applications-system-symbolic'},
        {id: 'g2', name: 'Term two', icon: 'applications-system-symbolic'},
        {id: 'g3', name: 'Term three', icon: 'applications-system-symbolic'},
    ]);
    sc.addProvider(list);
    sc.addProvider(grid);
    if (!list.display || !grid.display)
        throw new Error('test providers refused by the search');
    benchProviders = {list, grid};
    return benchProviders;
}

async function openSearch(ctx) {
    const {list, grid} = setProviders();
    const sc = Main.overview.searchController;
    await openOverview(false);
    // Keyboard focus on the entry before the text, like real typing: a set_text on an entry without focus leaves
    // Clutter's input method in an inconsistent state ("clutter_input_focus_set_cursor_location: assertion
    // 'clutter_input_focus_is_focused' failed"), and the nested Shell stopped when the test window of the next
    // scenario (previews) appeared.
    Main.overview.searchEntry.grab_key_focus();
    removeRemoteProviders();
    if (FAKE_REMOTE) {
        ctx.fakeRemote = {...makeProvider('m3e-bench-fake-remote', null, [
            {id: 'f1', name: 'Remote term', icon: 'text-x-generic-symbolic'}]), isRemoteProvider: true};
        sc.addProvider(ctx.fakeRemote);
    }
    Main.overview.searchEntry.set_text('term');
    const found = r => r.display.visible && findActor(r.display, e => e.has_style_class_name?.(
        r === list ? 'list-search-result' : 'grid-search-result'));
    if (!await waitUntil(() => found(list) && found(grid), 4000))
        throw new Error('test results missing');
    await wait(200);
    verifyNoRemote();
    // Default result (:selected) switched off (the entry keeps the focus, see below): the states are forced by the
    // bench.
    sc._searchResults.highlightDefault(false);
    const listResults = findAllByClass(list.display, 'list-search-result');
    const gridResults = findAllByClass(grid.display, 'grid-search-result');
    if (listResults.length < 3 || gridResults.length < 3)
        throw new Error(`incomplete test results: ${listResults.length} in list, ${gridResults.length} in grid`);
    // Label of the 3rd list result (no description) at the bench size: colour measured.
    const title = findActor(listResults[2], e => e instanceof St.Label);
    title.style = TEXT_SIZE;
    const entry = Main.overview.searchEntry;
    entry.style = TEXT_SIZE;
    // Entry without :focus for the measurement, keyboard focus left in place: removing it (set_key_focus(null))
    // made accessibility walk a destroyed actor ("clutter_actor_get_accessible: assertion failed") and the nested
    // Shell stopped at the next scenario. The pseudo-class is only set again by SearchController on a focus
    // change; cursor hidden (it would go through the text measurement).
    entry.remove_style_pseudo_class('focus');
    entry.clutter_text.set_cursor_visible(false);
    // Default result: the 1st list result gets the :selected pseudo-class, as SearchResultsView._setSelected does
    // for the result that Enter launches (the real default result here is an app of the apps provider, first).
    listResults[0].add_style_pseudo_class('selected');
    ctx.defaultResult = listResults[0];
    ctx.actors = {entry, section: findActor(list.display, e => e.has_style_class_name?.('search-section-content')),
        defaultResult: listResults[0], list: listResults[1], listText: listResults[2], grid: gridResults[1]};
}

async function closeSearch(ctx) {
    ctx.defaultResult?.remove_style_pseudo_class('selected');
    ctx.defaultResult = null;
    if (ctx.fakeRemote) {
        Main.overview.searchController.removeProvider(ctx.fakeRemote);
        ctx.fakeRemote = null;
    }
    const a = ctx.actors;
    ctx.actors = null;
    if (a) {
        a.entry.style = null;
        a.entry.clutter_text.set_cursor_visible(true);
    }
    Main.overview.searchEntry.grab_key_focus();
    Main.overview.searchEntry.set_text('');
    await closeOverview();
}

export const SEARCH_SURFACES = {
    // Search: overview open (Main.overview.show, signal `shown`), text "term" set through the entry's API
    // (searchEntry.set_text, no typing), two in-process test providers (list and grid, three results each; D-Bus
    // providers of the nested Shell are not guaranteed); entry without :focus (keyboard focus kept), default result
    // switched off (highlightDefault(false)). Real entry (label at the bench size: text and icon colour, both
    // on_surface); list section container; 2nd list result (geometry, layers); 3rd (title at the bench size); 2nd
    // grid result.
    search: {
        open: openSearch,
        cells: ctx => [
            {row: 'search-bar', actor: ctx.actors.entry, margin: 12},
            {row: 'search-section', actor: ctx.actors.section, margin: 4},
            {row: 'search-default', actor: ctx.actors.defaultResult, margin: 2},
            {row: 'search-list', actor: ctx.actors.list, margin: 2},
            {row: 'search-list-text', actor: ctx.actors.listText, margin: 2},
            {row: 'search-grid', actor: ctx.actors.grid, margin: 2},
        ],
        states: ['normal', 'hover', 'pressed', 'focus'],
        close: closeSearch,
    },
};
