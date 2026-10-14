/** Native constraints shared by Save and Continue, before busy disables controls. */
export function validateSetupForm(form, invalid) {
  if (!form) return true;
  for (const control of form.querySelectorAll('input,select,textarea')) {
    if (control.willValidate && !control.validity.valid) { control.setAttribute('aria-invalid', 'true'); control.setAttribute('aria-describedby', 'setup-error'); }
    else { control.removeAttribute('aria-invalid'); control.removeAttribute('aria-describedby'); }
  }
  if (form.checkValidity()) return true;
  invalid();
  const first = form.querySelector(':invalid');
  // FAQ constraints can sit inside a collapsed details element.
  for (let parent = first?.parentElement; parent; parent = parent.parentElement) {
    if (parent.tagName === 'DETAILS') parent.open = true;
  }
  form.reportValidity();
  first?.focus();
  return false;
}
