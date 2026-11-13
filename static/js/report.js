/* Preview controls never enter the submitted document. */
document.addEventListener('DOMContentLoaded', () => {
  const fields = [...document.querySelectorAll('[data-report-meta-input]')];
  const status = document.getElementById('metadata-status');
  const sync = () => {
    fields.forEach(input => document.querySelectorAll(`[data-report-meta="${input.dataset.reportMetaInput}"]`).forEach(node => {
      node.textContent = input.value;
      node.classList.toggle('empty-metadata', !input.value.trim());
    }));
    const missing = fields.filter(input => !input.value.trim()).map(input => input.dataset.label);
    if (status) status.textContent = missing.length ? `Przed oddaniem uzupełnij: ${missing.join(', ').toLowerCase()}.` : 'Dane na stronie tytułowej są uzupełnione.';
  };
  fields.forEach(input => input.addEventListener('input', sync));
  document.addEventListener('bipol:report-replaced', sync);  // treść podmieniona poprawkami autora
  sync();
  const resetDrawing = () => {
    document.body.classList.remove('print-drawing','plain-drawing','a2-drawing');
    document.getElementById('drawing-page-size')?.remove();
  };
  window.addEventListener('afterprint', resetDrawing);
  for (const [id, plain, a2] of [['print-drawing-plain',true,false],['print-drawing-grid',false,false],['print-drawing-a2',false,true]]) {
    document.getElementById(id)?.addEventListener('click', async () => {
      resetDrawing();
      document.body.classList.add('print-drawing');
      document.body.classList.toggle('plain-drawing',plain);
      document.body.classList.toggle('a2-drawing',a2);
      const style=document.createElement('style');style.id='drawing-page-size';
      style.textContent=`@page {size:${a2?'A2':'A4'} portrait;margin:${a2?'20mm':'10mm'};@bottom-center{content:none;}}`;document.head.append(style);
      await document.fonts.ready;window.print();
    });
  }
  document.getElementById('print-report')?.addEventListener('click', async () => {
    resetDrawing();
    await document.fonts.ready;
    window.print();
  });
});
