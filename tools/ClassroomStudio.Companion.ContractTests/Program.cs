using ClassroomStudio.Companion;

var expected = new HashSet<string>(StringComparer.Ordinal) { "launch_classroom_studio", "list_windows", "read_status", "find_control", "click_control", "read_visible_text", "take_screenshot", "read_application_log", "export_combined_bundle_to_staging", "list_bundle_files", "verify_bundle_manifest", "verify_sha256_manifest" };
var actual = ToolCatalog.Names.ToHashSet(StringComparer.Ordinal);
if (!actual.SetEquals(expected)) throw new InvalidOperationException("Companion tool allowlist changed unexpectedly.");
var forbidden = new[] { "flash_firmware", "copy_to_circuitpy", "serial_write", "guard_on", "guard_off", "halt", "reset_board", "actuator_control", "keyboard_control", "mouse_control", "install_driver", "release_publish" };
if (actual.Overlaps(forbidden)) throw new InvalidOperationException("A prohibited hardware or release tool was exposed.");
foreach (var query in new[] { "Guard ON", "Guard OFF", "Run", "Stop", "Connect", "flash firmware", "reset board", "Pico USB", "Arduino" }) if (!DangerousControlPolicy.IsDenied(query)) throw new InvalidOperationException("Safety policy did not deny: " + query);
foreach (var query in new[] { "Desktop", "Login / DC", "Character Dashboard", "Combined Guard Bundle", "Take screenshot" }) if (DangerousControlPolicy.IsDenied(query)) throw new InvalidOperationException("Safety policy denied a safe diagnostic/export control: " + query);
if (BundleValidator.RequiredFiles.Length != 19) throw new InvalidOperationException("Bundle contract changed unexpectedly.");
Console.WriteLine("Classroom Studio companion contract tests: passed");
