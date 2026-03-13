"""
RomMate - Operations
Handles all ROM processing operations (CHD, M3U, Health, Validate).
Each function receives a callbacks dict to communicate with the UI.
"""

import os
import platform
import subprocess
import threading
import shutil
from tkinter import messagebox

from core.file_utils import find_multidisc_games, create_m3u_file
from gui.dialogs import show_format_choice_dialog
from utils.i18n import _


def _check_chdman(converter, callbacks):
    """Shared chdman check used by CHD operations. Returns True if ready."""
    log  = callbacks['log']
    done = callbacks['complete']

    converter.chdman_path = converter.find_chdman()
    if not converter.chdman_path:
        log("[x] chdman not found")
        if platform.system() == 'Linux':
            log("\nOffering automatic installation...")
            if converter.prompt_install_chdman():
                log("\nInstallation in progress...")
                log("Please complete installation in the terminal, then try again.")
            else:
                log("\n[!] Installation cancelled")
        else:
            log("\nchdman is required for CHD conversion.")
            log("It should be in the tools/ folder.")
            messagebox.showerror(
                _("chdman Not Found"),
                _("chdman is required for CHD conversion.\n\nIt should be bundled in the tools/ folder.")
            )
        done(success=False)
        return False

    try:
        test = subprocess.run(
            [converter.chdman_path, '--help'],
            capture_output=True, text=True, timeout=5
        )
        if test.returncode != 0 and platform.system() == 'Linux':
            if 'error while loading shared libraries' in test.stderr:
                log("[x] chdman has missing dependencies")
                log(f"Error: {test.stderr[:150]}")
                if converter.prompt_install_chdman():
                    log("\nInstallation in progress...")
                    log("Please complete installation in the terminal, then try again.")
                else:
                    log("\n[!] Installation cancelled")
                done(success=False)
                return False
    except Exception as e:
        log(f"[!] Could not test chdman: {e}")

    log(f"[✓] chdman: {converter.chdman_path}")
    return True


# ------------------------------------------------------------------ #
#  CHD Conversion                                                      #
# ------------------------------------------------------------------ #

def convert_to_chd(folder, delete_after, converter, callbacks):
    """Convert CUE/GDI/CDI/ISO files to CHD format."""
    log      = callbacks['log']
    progress = callbacks['progress']
    animate  = callbacks['animate']
    cancel   = callbacks['cancel']
    done     = callbacks['complete']
    ret      = callbacks['return']

    try:
        progress("CHD Conversion", "Checking for chdman tool...", 0, 1)

        if not _check_chdman(converter, callbacks):
            return

        progress("CHD Conversion", "Scanning for disc images...")

        converted, skipped, failed = converter.convert_folder(
            folder,
            delete_after=delete_after,
            log_callback=log,
            progress_callback=lambda cur, tot, fn: progress(
                "Converting to CHD", f"Processing file {cur} of {tot}", cur, tot, fn),
            animation_callback=animate,
            cancel_check=cancel
        )

        if cancel():
            ret()
            return

        if converted == 0 and skipped == 0 and failed == 0:
            log("\n[x] No convertible files found")
            log("Supported formats: CUE, GDI, CDI, ISO")
            messagebox.showinfo(_("No Files"), _("No convertible disc images found."))
            done(success=False)
            return

        log("\n" + "=" * 60)
        log(f"Converted: {converted}  |  Skipped: {skipped}  |  Failed: {failed}")
        log("=" * 60)

        if cancel():
            ret()
            return

        done(success=failed == 0, converted=converted, skipped=skipped, failed=failed)
        messagebox.showinfo(
            _("Conversion Complete"),
            f"CHD conversion finished!\n\nConverted: {converted}\nSkipped: {skipped}\nFailed: {failed}"
        )

    except Exception as e:
        log(f"\n[x] Error: {str(e)}")
        messagebox.showerror(_("Error"), f"An error occurred:\n{str(e)}")
        done(success=False)


# ------------------------------------------------------------------ #
#  M3U Creation                                                        #
# ------------------------------------------------------------------ #

def create_m3u_files(folder, m3u_creator, root, callbacks):
    """Create M3U playlists for multi-disc games."""
    log      = callbacks['log']
    progress = callbacks['progress']
    done     = callbacks['complete']
    ret      = callbacks['return']

    try:
        progress("M3U Creator", "Detecting available disc formats...")

        created, skipped, cancelled = m3u_creator.auto_detect_and_create(
            folder,
            log_callback=log,
            progress_callback=lambda cur, tot, fn: progress(
                "Creating M3U Playlists", f"Processing game {cur} of {tot}", cur, tot, fn),
            format_choice_callback=lambda: show_format_choice_dialog(root)
        )

        if cancelled:
            ret()
            return

        if created == 0 and skipped == 0:
            log("[x] No multi-disc games found")
            log("\nMake sure files follow naming conventions like:")
            log("  • Game Name (Disc 1).cue")
            log("  • Game Name (Disc 2).chd")
            messagebox.showinfo(_("No Games Found"), _("No multi-disc games were found."))
            done(success=False)
        else:
            log(f"\n{'=' * 60}")
            log(f"Created: {created}  |  Skipped: {skipped}")
            log(f"{'=' * 60}\nALL OPERATIONS COMPLETE\n{'=' * 60}")
            done(success=True, converted=created, skipped=skipped)
            messagebox.showinfo(
                _("M3U Creation Complete"),
                f"M3U playlist creation finished!\n\nCreated: {created}\nSkipped: {skipped}"
            )

    except Exception as e:
        log(f"\n[x] Error: {str(e)}")
        messagebox.showerror(_("Error"), f"An error occurred:\n{str(e)}")
        done(success=False)


# ------------------------------------------------------------------ #
#  CHD + M3U Combined                                                  #
# ------------------------------------------------------------------ #

def convert_and_create_m3u(folder, delete_after, converter, callbacks):
    """Convert to CHD then create M3U playlists."""
    log      = callbacks['log']
    progress = callbacks['progress']
    animate  = callbacks['animate']
    cancel   = callbacks['cancel']
    done     = callbacks['complete']
    ret      = callbacks['return']

    try:
        progress("CHD + M3U", "Step 1: Checking for chdman...")

        if not _check_chdman(converter, callbacks):
            return

        log("\n=== STEP 1: CHD Conversion ===")

        converted, skipped, failed = converter.convert_folder(
            folder,
            delete_after=delete_after,
            log_callback=log,
            progress_callback=lambda cur, tot, fn: progress(
                "Step 1: Converting to CHD", f"Processing file {cur} of {tot}", cur, tot, fn),
            animation_callback=animate,
            cancel_check=cancel
        )

        log(
            f"\nStep 1 complete: Converted {converted} file(s)"
            if converted > 0 or skipped > 0
            else "No files found to convert"
        )

        log("\n=== STEP 2: M3U Creation ===\n")
        progress("Step 2: Creating M3U", "Scanning for multi-disc games...")

        multidisc_games = find_multidisc_games(
            folder, extensions=["*.chd"], log_callback=log
        )
        created = 0

        if multidisc_games:
            total_games = len(multidisc_games)
            log(f"Found {total_games} multi-disc game(s)\n")
            for idx, (game_name, disc_files) in enumerate(multidisc_games.items(), 1):
                progress(
                    "Step 2: Creating M3U",
                    f"Processing game {idx} of {total_games}",
                    idx, total_games, f"{game_name}.m3u"
                )
                if create_m3u_file(game_name, disc_files, folder, log):
                    created += 1
            log(f"\nStep 2 complete: Created {created} M3U file(s)")
        else:
            log("No multi-disc games found")

        log("\n" + "=" * 60 + "\nALL OPERATIONS COMPLETE\n" + "=" * 60)

        if cancel():
            ret()
            return

        done(success=True, converted=created, skipped=0, failed=0)

    except Exception as e:
        log(f"\n[x] Error: {str(e)}")
        messagebox.showerror(_("Error"), f"An error occurred:\n{str(e)}")
        done(success=False)


# ------------------------------------------------------------------ #
#  ROM Health Check                                                    #
# ------------------------------------------------------------------ #

def check_rom_health(folder, rom_health, chd_converter, root, callbacks, after_fn):
    """Run ROM health check. after_fn is root.after for thread-safe UI calls."""
    log      = callbacks['log']
    progress = callbacks['progress']
    cancel   = callbacks['cancel']
    done     = callbacks['complete']
    ret      = callbacks['return']

    def run():
        try:
            results = rom_health.check_folder(
                folder,
                log_callback=log,
                progress_callback=lambda cur, tot, fn: progress(
                    "Checking ROM Health", f"Verifying file {cur} of {tot}", cur, tot, fn),
                cancel_check=cancel
            )

            if cancel():
                ret()
                return

            total_verified = (results['chd_verified'] + results['cue_verified'] +
                              results['cart_verified'])
            total_issues   = (results['chd_failed'] + results['cue_failed'] +
                              results['cart_has_header'] + results['cart_unknown'] +
                              results['cart_failed'])

            log("\n" + "=" * 60 + "\nSummary:\n" + "=" * 60)

            if results['chd_verified'] + results['chd_failed'] > 0:
                log(f"CHD Files:  [✓] {results['chd_verified']} verified  |  [x] {results['chd_failed']} failed")
            if results['cue_verified'] + results['cue_failed'] > 0:
                log(f"CUE/BIN:    [✓] {results['cue_verified']} verified  |  [x] {results['cue_failed']} failed")
            if (results['cart_verified'] + results['cart_has_header'] +
                    results.get('cart_hacks', 0) + results['cart_unknown'] + results['cart_failed']) > 0:
                log(
                    f"Game Files: [✓] {results['cart_verified']} verified  |  "
                    f"[!] {results['cart_has_header']} have headers  |  "
                    f"[!] {results.get('cart_hacks', 0)} ROM hacks  |  "
                    f"[?] {results['cart_unknown']} unknown  |  "
                    f"[x] {results['cart_failed']} failed"
                )
            log("=" * 60)

            if cancel():
                ret()
                return

            if results.get('cart_has_header', 0) > 0:
                after_fn(100, lambda: callbacks['offer_header_fix'](results))

            if total_issues == 0 and total_verified > 0:
                done(success=True, converted=total_verified, skipped=0, failed=0)
            elif total_verified > 0:
                done(success=False, converted=total_verified, skipped=0, failed=total_issues)
            else:
                done(success=False, converted=0, skipped=0, failed=total_issues)

        except Exception as e:
            import traceback
            log(f"\n[x] Error: {str(e)}")
            log(traceback.format_exc())
            done(success=False)
        finally:
            callbacks['set_processing'](False)

    threading.Thread(target=run, daemon=True).start()


# ------------------------------------------------------------------ #
#  ROM Name Validation                                                 #
# ------------------------------------------------------------------ #

def validate_rom_names(folder, name_validator, root, callbacks, after_fn):
    """Validate and fix ROM names."""
    log    = callbacks['log']
    cancel = callbacks['cancel']
    done   = callbacks['complete']
    ret    = callbacks['return']

    def run():
        try:
            log(f"ROM Name Validator\nFolder: {folder}\n{'=' * 60}")
            results = name_validator.validate_folder(
                folder,
                log_callback=log,
                progress_callback=lambda cur, tot, fn:
                    log(f"Processing file {cur} of {tot}: {fn}"),
                cancel_check=cancel
            )

            if cancel():
                ret()
                return

            log("\n" + "=" * 60 + "\nSummary:\n" + "=" * 60)

            if not results:
                log("[✓] All ROM names are correct!")
                done(success=True, converted=0, skipped=0, failed=0)
            else:
                log(f"Found {len(results)} ROM(s) that need renaming")
                after_fn(100, lambda: callbacks['show_rename_dialog'](results))

        except Exception as e:
            import traceback
            log(f"\n[x] Error: {str(e)}")
            log(traceback.format_exc())
            done(success=False, converted=0, skipped=0, failed=1)

    threading.Thread(target=run, daemon=True).start()
