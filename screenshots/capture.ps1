Add-Type -AssemblyName System.Windows.Forms
Add-Type -AssemblyName System.Drawing

Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public class CaptureUtil {
    [DllImport("user32.dll")]
    public static extern IntPtr FindWindow(string lpClassName, string lpWindowName);
    [DllImport("user32.dll")]
    public static extern bool GetWindowRect(IntPtr hWnd, out RECT lpRect);
    [DllImport("user32.dll")]
    public static extern bool SetForegroundWindow(IntPtr hWnd);
    [StructLayout(LayoutKind.Sequential)]
    public struct RECT { public int Left, Top, Right, Bottom; }
}
'@

function Capture-Window {
    param($title, $filename, $waitSecs = 3)
    Start-Sleep -Seconds $waitSecs
    $hwnd = [IntPtr]::Zero
    for ($i = 0; $i -lt 15; $i++) {
        $hwnd = [CaptureUtil]::FindWindow("TkTopLevel", $title)
        if ($hwnd -ne [IntPtr]::Zero) { break }
        Start-Sleep -Milliseconds 300
    }
    if ($hwnd -eq [IntPtr]::Zero) {
        Write-Host "Window '$title' not found"
        return $false
    }
    [CaptureUtil]::SetForegroundWindow($hwnd) | Out-Null
    Start-Sleep -Milliseconds 400

    $rect = New-Object CaptureUtil+RECT
    [CaptureUtil]::GetWindowRect($hwnd, [ref]$rect)
    $w = $rect.Right - $rect.Left
    $h = $rect.Bottom - $rect.Top

    if ($w -le 0 -or $h -le 0) {
        Write-Host "Invalid window size: $w x $h"
        return $false
    }

    $bmp = New-Object System.Drawing.Bitmap($w, $h)
    $gfx = [System.Drawing.Graphics]::FromImage($bmp)
    $gfx.CopyFromScreen($rect.Left, $rect.Top, 0, 0, (New-Object System.Drawing.Size($w, $h)))
    $gfx.Dispose()
    $bmp.Save($filename, [System.Drawing.Imaging.ImageFormat]::Png)
    $bmp.Dispose()
    Write-Host "Saved: $filename ($w x $h)"
    return $true
}

$app = Start-Process python -ArgumentList "main.pyw" -PassThru -WindowStyle Normal
$ok = Capture-Window "DeepSeek Proxy" "screenshots\main_window.png" 2

# Try to capture settings dialog
function Send-Click {
    param($hwnd, $x, $y)
    $lparam = ($y -shl 16) -bor $x
    $WM_LBUTTONDOWN = 0x201
    $WM_LBUTTONUP = 0x202
    # Simple mouse click simulation won't work easily from PS
}

$app.Kill()
Start-Sleep -Milliseconds 500

Write-Host "Done. ok=$ok"
