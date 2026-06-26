# Development Notes

## on_top behavior and activation

### Observation
Using a transient topmost pulse in `put_on_top` (`HWND_TOPMOST` followed by `HWND_NOTOPMOST`) with `SWP_NOACTIVATE` can make a window appear to behave like it is still always-on-top until a later activation event occurs.

### Why this happens
Changing z-order without activation updates stacking, but does not always run through the same foreground activation/deactivation lifecycle that occurs when a window is activated.

When `activate=True`, Windows processes a normal focus transition. After that, when the user clicks another window, the previously raised window yields naturally in z-order.

### Practical guidance
- Keep `on_top` behavior using `activate=True` when the desired UX is:
  - bring window to front now,
  - allow immediate normal yielding when user interacts elsewhere.
- Be cautious with non-activating z-order pulses if the UX must avoid sticky top behavior.

### Current project choice
The call site currently uses `put_on_top(hwnd, activate=True)` to produce the desired behavior during interactive use.
