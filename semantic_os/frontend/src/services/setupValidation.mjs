/** Native constraints shared by Save and Continue, before busy disables controls. */
export async function validateSetupForm(form, invalid) {
  if (!form) return true;
  for (const control of form.querySelectorAll('input,select,textarea')) {
    const descriptions = (control.getAttribute('aria-describedby') || '').split(/\s+/).filter(value => value && value !== 'setup-error');
    if (control.willValidate && !control.validity.valid) { control.setAttribute('aria-invalid', 'true'); descriptions.push('setup-error'); }
    else { control.removeAttribute('aria-invalid');  }
    if(descriptions.length) control.setAttribute('aria-describedby', descriptions.join(' '));
    else control.removeAttribute('aria-describedby');
  }
  if (form.checkValidity()) return true;
  await invalid();
  const first = form.querySelector('input:invalid,select:invalid,textarea:invalid');
  // FAQ constraints can sit inside a collapsed details element.
  for (let parent = first?.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === 'DETAILS') parent.open = true;
  }
  // Use the rendered, localized error instead of a competing native popup.
  first?.focus();
  return false;
}
