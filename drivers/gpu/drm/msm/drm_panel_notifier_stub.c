/* SPDX-License-Identifier: GPL-2.0 */
/* Minimal stub of drm_panel_notifier for FocalTech touch driver.
 * Real implementation is in vendor DRM changes not present in CAF tree.
 * No-op registration keeps touch driver functional.
 */
#include <linux/module.h>
#include <drm/drm_panel.h>

int drm_panel_notifier_register(struct drm_panel *panel,
				struct notifier_block *nb)
{
	return 0;
}
EXPORT_SYMBOL(drm_panel_notifier_register);

int drm_panel_notifier_unregister(struct drm_panel *panel,
				  struct notifier_block *nb)
{
	return 0;
}
EXPORT_SYMBOL(drm_panel_notifier_unregister);

int drm_panel_notifier_call_chain(struct drm_panel *panel,
				  unsigned long val, void *v)
{
	return 0;
}
EXPORT_SYMBOL(drm_panel_notifier_call_chain);
