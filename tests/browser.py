"""Cloud-only live Shiny behavior checks. Requires Playwright and Chromium."""
import json
import os
import zipfile
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

URL = os.getenv('SHINY_URL', 'http://127.0.0.1:3838')
SCREENS = Path(os.getenv('SCREEN_DIR', 'docs/design/screens'))
SCREENS.mkdir(parents=True, exist_ok=True)

def contrast(a, b):
    def luminance(color):
        values = [int(color[i:i+2], 16) / 255 for i in (1, 3, 5)]
        return sum(weight * (v / 12.92 if v <= .04045 else ((v + .055) / 1.055) ** 2.4) for weight, v in zip((.2126, .7152, .0722), values))
    high, low = sorted([luminance(a), luminance(b)], reverse=True)
    return (high + .05) / (low + .05)

def idle(page):
    page.wait_for_function("!document.documentElement.classList.contains('shiny-busy')")
    expect(page.locator('#run')).to_be_enabled()
    page.wait_for_timeout(300)  # Shiny input debounce and updateSelectInput round trip.

def run(page):
    page.get_by_role('button', name='Run analysis', exact=True).click()
    expect(page.locator('#status')).to_contain_text('Analysis complete.')
    idle(page)

def plot_values(page):
    return page.locator('#clusterPlot').evaluate("e => e.data.map(t => ({name:t.name,x:t.x,y:t.y,text:t.text}))")

report = []
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.getenv('CHROMIUM', '/usr/bin/chromium'), args=['--no-sandbox'])
    for width in [320, 768, 1024, 1440]:
        for theme in ['light', 'dark']:
            context = browser.new_context(viewport={'width': width, 'height': 1000}, color_scheme=theme, reduced_motion='reduce', accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda e: errors.append(str(e)))
            response = page.goto(URL, wait_until='domcontentloaded')
            assert response.status == 200
            page.wait_for_function('window.Shiny && Shiny.shinyapp && Shiny.shinyapp.$socket.readyState === 1')
            idle(page)
            page.evaluate("window.busyVerified=false; jQuery(document).on('shiny:busy.verify', () => { window.busyVerified = document.getElementById('run').disabled && document.getElementById('results').getAttribute('aria-busy') === 'true'; })")
            run(page)
            assert page.evaluate('window.busyVerified')
            expect(page.locator('#status')).to_contain_text('83 players · 5 clusters')
            page.wait_for_function("document.querySelectorAll('.scatterlayer .point').length === 83")
            assert page.evaluate('window.Plotly.version') == '2.25.2', 'Expected the remediated Plotly bundle'
            page.evaluate('document.fonts.ready')
            assert page.evaluate("document.fonts.check('14px Geist') && document.fonts.check('14px \"Geist Mono\"')")
            background = '#ffffff' if theme == 'light' else '#0a0a0b'
            muted = '#66666f' if theme == 'light' else '#92929b'
            focus = '#3b73d9' if theme == 'light' else '#6f9fe0'
            assert contrast(muted, background) >= 4.5 and contrast(focus, background) >= 3
            for color in ['#2874b8', '#b45417', '#16845d', '#a74c9f', '#a84142']:
                assert contrast(color, background) >= 3
            original = plot_values(page)
            run(page)
            assert plot_values(page) == original, 'Repeated plot differs'
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), f'Body overflow at {width}'
            # Keyboard path: focus ring, native selector, and player details.
            page.locator('#player').focus()
            assert page.locator('#player').evaluate("e => getComputedStyle(e).outlineStyle") == 'solid'
            page.keyboard.press('ArrowDown')
            page.keyboard.press('Enter')
            page.keyboard.press('Tab')
            selected = page.locator('#player').input_value()
            expect(page.locator('#detail')).to_contain_text(selected)
            page.get_by_role('tab', name='Table', exact=True).click()
            expect(page.locator('.dataTables_info')).to_contain_text('83 entries')
            page.get_by_label('Selected cluster for tabulation').select_option('1')
            expect(page.locator('.dataTables_info')).not_to_contain_text('83 entries')
            page.get_by_label('Selected cluster for tabulation').select_option('All')
            expect(page.locator('.dataTables_info')).to_contain_text('83 entries')
            search = page.get_by_label('Search:')
            search.fill('ALL Hakis')
            expect(page.locator('.dataTables_info')).to_contain_text('1 entries')
            search.fill('')
            expect(page.locator('.dataTables_info')).to_contain_text('83 entries')
            with page.expect_download() as download:
                page.get_by_role('button', name='CSV', exact=True).click()
            csv = Path(download.value.path()).read_text(encoding='utf-8-sig')
            assert 'ALL Hakis' in csv and 'Cluster' in csv
            if width == 1440 and theme == 'light':
                for label in ['Excel', 'PDF']:
                    with page.expect_download() as extra:
                        page.get_by_role('button', name=label, exact=True).click()
                    path = extra.value.path()
                    if label == 'PDF':
                        assert Path(path).read_bytes().startswith(b'%PDF')
                    else:
                        with zipfile.ZipFile(path) as book:
                            assert 'xl/worksheets/sheet1.xml' in book.namelist()
                with page.expect_popup() as popup:
                    page.get_by_role('button', name='Print', exact=True).click()
                expect(popup.value.locator('body')).to_contain_text('ALL Hakis')
                popup.value.close()
            page.screenshot(path=str(SCREENS / f'{width}-{theme}-table.png'), full_page=True)
            page.get_by_role('tab', name='Chart', exact=True).click()
            page.get_by_label('Cluster on per-game metrics').check()
            expect(page.locator('#status')).to_contain_text('Settings changed')
            expect(page.locator('#detail')).not_to_contain_text(selected)
            run(page)
            assert plot_values(page) != original
            page.screenshot(path=str(SCREENS / f'{width}-{theme}-chart.png'), full_page=True)
            assert page.locator('#run').evaluate('e => e.getBoundingClientRect().height') >= 44
            assert page.locator('#results').get_attribute('aria-busy') == 'false'
            # Empty and bounds errors must clear current results, then recover.
            page.get_by_role('button', name='Clear filters', exact=True).click()
            idle(page)
            page.get_by_label('Number of clusters').fill('15')
            page.evaluate("$('#kills').data('ionRangeSlider').update({from:74,to:74}); $('#kills').trigger('change')")
            idle(page)
            page.get_by_role('button', name='Run analysis', exact=True).click()
            expect(page.locator('#status')).to_contain_text('valid distinct rows')
            expect(page.locator('#clusterPlot')).not_to_be_visible()
            page.get_by_role('button', name='Reset example', exact=True).click()
            idle(page)
            page.evaluate("$('#games').data('ionRangeSlider').update({from:6,to:6}); $('#games').trigger('change')")
            page.evaluate("$('#kills').data('ionRangeSlider').update({from:74,to:74}); $('#kills').trigger('change')")
            idle(page)
            page.get_by_role('button', name='Run analysis', exact=True).click()
            expect(page.locator('#status')).to_contain_text('No players match these filters')
            page.get_by_role('button', name='Clear filters', exact=True).click()
            idle(page)
            run(page)
            expect(page.locator('#status')).to_contain_text('123 players')
            page.get_by_label('Compare metrics').select_option('K+A/D vs Damage Difference per Game')
            idle(page)
            run(page)
            assert 'K+A/D' in page.locator('#detail').inner_text()
            expect(page.get_by_label('K+A/D', exact=True)).to_be_visible()
            expect(page.get_by_label('Damage difference per game', exact=True)).to_be_visible()
            page.get_by_role('button', name='Reset example', exact=True).click()
            idle(page)
            run(page)
            expect(page.locator('#status')).to_contain_text('83 players')
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth')
            assert not errors, errors
            report.append({'width': width, 'theme': theme, 'reduced_motion': True, 'plotly_js': page.evaluate('window.Plotly.version'), 'checks': 'repeat/run/busy/per-game/filter/bounds/empty/reset/table/search/CSV/player/focus/contrast/fonts/no-overflow', 'page_errors': errors})
            print(json.dumps(report[-1]), flush=True)
            context.close()
    browser.close()
Path(os.getenv('BROWSER_REPORT', 'browser-report.json')).write_text(json.dumps(report, indent=2))
