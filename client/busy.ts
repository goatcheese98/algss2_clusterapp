// Shiny emits these lifecycle events through jQuery. No payload is consumed.
interface EventSource { on(event: string, handler: () => void): void }
declare const jQuery: (target: Document) => EventSource;
const setBusy = (busy: boolean): void => {
  const button = document.getElementById('run');
  if (button instanceof HTMLButtonElement) button.disabled = busy;
  const results = document.getElementById('results');
  if (results instanceof HTMLElement) results.setAttribute('aria-busy', String(busy));
};
jQuery(document).on('shiny:busy', () => setBusy(true));
jQuery(document).on('shiny:idle', () => setBusy(false));
// Older DataTables Buttons emits anchors without href or role. Supply the
// button contract while retaining its existing Enter/click export handlers.
const labelExportButtons = (): void => {
  document.querySelectorAll('.dt-buttons a.dt-button').forEach((node) => {
    if (node instanceof HTMLAnchorElement) node.setAttribute('role', 'button');
  });
};
new MutationObserver(labelExportButtons).observe(document.body, { childList: true, subtree: true });
document.addEventListener('keydown', (event: KeyboardEvent) => {
  if (event.key !== ' ' || !(event.target instanceof HTMLAnchorElement)) return;
  if (event.target.matches('.dt-buttons a.dt-button')) {
    event.preventDefault();
    event.target.click();
  }
});
