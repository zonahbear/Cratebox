//! Windows-only bits: the audio thread's MMCSS "Pro Audio" class, message boxes for startup problems
//! (a GUI app has no terminal), attaching to the terminal for --version, and the drive letters the file
//! picker lists. Called from the UI thread, except `pro_audio_thread` (the audio callback, once).

use std::path::PathBuf;
use std::sync::atomic::{AtomicBool, Ordering};
use windows::core::{w, HSTRING};
use windows::Win32::System::Threading::{AvSetMmThreadCharacteristicsW, AvSetMmThreadPriority, AVRT_PRIORITY_HIGH};
use windows::Win32::UI::WindowsAndMessaging::{MessageBoxW, MB_ICONWARNING, MB_OK};

/// Joins the calling (audio callback) thread to the "Pro Audio" MMCSS task, the way pro audio apps on
/// Windows get their callbacks run ahead of everything else. Needs no rights; if it fails the thread
/// stays at normal priority. Windows undoes it when the thread ends.
pub fn pro_audio_thread() {
    static WARNED: AtomicBool = AtomicBool::new(false);
    let mut task = 0u32;
    match unsafe { AvSetMmThreadCharacteristicsW(w!("Pro Audio"), &mut task) } {
        Ok(h) => { let _ = unsafe { AvSetMmThreadPriority(h, AVRT_PRIORITY_HIGH) }; }
        Err(e) => if !WARNED.swap(true, Ordering::Relaxed) { eprintln!("cratebox: no Pro Audio priority for the audio thread ({e}), running at normal priority"); },
    }
}

pub fn message_box(text: &str) {
    unsafe { MessageBoxW(None, &HSTRING::from(text), w!("Cratebox"), MB_OK | MB_ICONWARNING); }
}

/// started from PowerShell or cmd: print there (--version, warnings); started from Explorer: nothing happens
pub fn attach_console() {
    use windows::Win32::System::Console::{AttachConsole, ATTACH_PARENT_PROCESS};
    let _ = unsafe { AttachConsole(ATTACH_PARENT_PROCESS) };
}

/// every drive letter in use (C:\, USB sticks, SD cards), for the file picker's places
pub fn drives() -> Vec<PathBuf> {
    use windows::Win32::Storage::FileSystem::GetLogicalDrives;
    let mask = unsafe { GetLogicalDrives() };
    (0..26u8).filter(|i| mask & (1 << i) != 0).map(|i| PathBuf::from(format!("{}:\\", (b'A' + i) as char))).collect()
}

/// a USB stick or card reader (Windows' "removable" drive type), not a fixed disk
pub fn removable(root: &std::path::Path) -> bool {
    use windows::Win32::Storage::FileSystem::GetDriveTypeW;
    const DRIVE_REMOVABLE: u32 = 2;
    unsafe { GetDriveTypeW(&HSTRING::from(root.as_os_str())) == DRIVE_REMOVABLE }
}

/// open a file, folder, URL or ms-settings: page with whatever Windows uses for it
pub fn open(target: &str) -> std::io::Result<std::process::Child> { std::process::Command::new("explorer.exe").arg(target).spawn() }

/// CPU time since boot in 100 ns ticks: (all, idle), for the header's CPU %
pub fn cpu_times() -> Option<(u64, u64)> {
    use windows::Win32::Foundation::FILETIME;
    use windows::Win32::System::Threading::GetSystemTimes;
    let (mut i, mut k, mut u) = (FILETIME::default(), FILETIME::default(), FILETIME::default());
    unsafe { GetSystemTimes(Some(&mut i), Some(&mut k), Some(&mut u)) }.ok()?;
    let t = |f: FILETIME| (f.dwHighDateTime as u64) << 32 | f.dwLowDateTime as u64;
    // kernel time includes idle time
    Some((t(k) + t(u), t(i)))
}

/// memory in use, MB
pub fn mem_used_mb() -> Option<u64> {
    use windows::Win32::System::SystemInformation::{GlobalMemoryStatusEx, MEMORYSTATUSEX};
    let mut m = MEMORYSTATUSEX { dwLength: std::mem::size_of::<MEMORYSTATUSEX>() as u32, ..Default::default() };
    unsafe { GlobalMemoryStatusEx(&mut m) }.ok()?;
    Some((m.ullTotalPhys - m.ullAvailPhys) / (1024 * 1024))
}

/// bytes received and sent since boot over the network adapters (hardware ones only, so filter
/// drivers and loopback aren't counted twice)
pub fn net_bytes() -> Option<(u64, u64)> {
    use windows::Win32::NetworkManagement::IpHelper::{FreeMibTable, GetIfTable2, MIB_IF_TABLE2};
    let mut t: *mut MIB_IF_TABLE2 = std::ptr::null_mut();
    if unsafe { GetIfTable2(&mut t) }.is_err() || t.is_null() { return None; }
    let (mut rx, mut tx) = (0u64, 0u64);
    unsafe {
        let rows = std::slice::from_raw_parts((*t).Table.as_ptr(), (*t).NumEntries as usize);
        for r in rows {
            if r.InterfaceAndOperStatusFlags._bitfield & 1 != 0 { rx += r.InOctets; tx += r.OutOctets; }
        }
        FreeMibTable(t as *const _);
    }
    Some((rx, tx))
}

/// the laptop battery: (percent, on AC); None on a desktop
pub fn battery() -> Option<(u32, bool)> {
    use windows::Win32::System::Power::{GetSystemPowerStatus, SYSTEM_POWER_STATUS};
    let mut s = SYSTEM_POWER_STATUS::default();
    unsafe { GetSystemPowerStatus(&mut s) }.ok()?;
    // 128 = no battery, 255 = unknown
    if s.BatteryFlag & 128 != 0 || s.BatteryFlag == 255 || s.BatteryLifePercent > 100 { return None; }
    Some((s.BatteryLifePercent as u32, s.ACLineStatus == 1))
}

/// Windows' own shutdown / restart (what the power menu's buttons do on Cratebox OS with systemctl)
pub fn power(then: &str) { let _ = std::process::Command::new("shutdown").args([if then == "reboot" { "/r" } else { "/s" }, "/t", "0"]).status(); }

/// Nicotine+ (Soulseek): on the PATH, or where its Windows installer puts it
pub fn nicotine() -> std::io::Result<std::process::Child> {
    std::process::Command::new("nicotine").spawn().or_else(|_| {
        let pf = std::env::var("ProgramFiles").unwrap_or_else(|_| r"C:\Program Files".into());
        std::process::Command::new(PathBuf::from(pf).join("Nicotine+").join("Nicotine+.exe")).spawn()
    })
}
