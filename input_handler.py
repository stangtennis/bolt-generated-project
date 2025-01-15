import logging
import win32api
import win32con
import win32com.client
import win32clipboard
import time
import pythoncom

logger = logging.getLogger(__name__)

class InputHandler:
    """Handle mouse and keyboard input events"""
    
    def __init__(self):
        """Initialize input handler"""
        # Initialize COM in this thread
        pythoncom.CoInitialize()
        
        self.shell = win32com.client.Dispatch("WScript.Shell")
        # Initialize virtual key mappings
        self.VIRTUAL_KEYS = {
            'Backspace': win32con.VK_BACK,
            'Tab': win32con.VK_TAB,
            'Enter': win32con.VK_RETURN,
            'Shift': win32con.VK_SHIFT,
            'Control': win32con.VK_CONTROL,
            'Alt': win32con.VK_MENU,
            'CapsLock': win32con.VK_CAPITAL,
            'Escape': win32con.VK_ESCAPE,
            'Space': win32con.VK_SPACE,
            'PageUp': win32con.VK_PRIOR,
            'PageDown': win32con.VK_NEXT,
            'End': win32con.VK_END,
            'Home': win32con.VK_HOME,
            'ArrowLeft': win32con.VK_LEFT,
            'ArrowUp': win32con.VK_UP,
            'ArrowRight': win32con.VK_RIGHT,
            'ArrowDown': win32con.VK_DOWN,
            'Insert': win32con.VK_INSERT,
            'Delete': win32con.VK_DELETE,
        }
        
        # Add number keys
        for i in range(10):
            self.VIRTUAL_KEYS[str(i)] = 0x30 + i  # 0-9 keys
        
        # Add letter keys
        for i in range(26):
            self.VIRTUAL_KEYS[chr(65 + i)] = 0x41 + i  # Uppercase
            self.VIRTUAL_KEYS[chr(97 + i)] = 0x41 + i  # Lowercase

    def __del__(self):
        """Cleanup when object is destroyed"""
        try:
            pythoncom.CoUninitialize()
        except:
            pass

    def handle_mouse_event(self, event_type: str, **kwargs) -> None:
        """Handle mouse events"""
        try:
            # Initialize COM for this method
            pythoncom.CoInitialize()
            
            if event_type == 'move':
                x = kwargs.get('x', 0)
                y = kwargs.get('y', 0)
                self.move_mouse(x, y)
            
            elif event_type == 'down':
                button = kwargs.get('button', 'left')
                if button == 'left':
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTDOWN, 0, 0, 0, 0)
                elif button == 'middle':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEDOWN, 0, 0, 0, 0)
                elif button == 'right':
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTDOWN, 0, 0, 0, 0)
            
            elif event_type == 'up':
                button = kwargs.get('button', 'left')
                if button == 'left':
                    win32api.mouse_event(win32con.MOUSEEVENTF_LEFTUP, 0, 0, 0, 0)
                elif button == 'middle':
                    win32api.mouse_event(win32con.MOUSEEVENTF_MIDDLEUP, 0, 0, 0, 0)
                elif button == 'right':
                    win32api.mouse_event(win32con.MOUSEEVENTF_RIGHTUP, 0, 0, 0, 0)
            
            elif event_type == 'wheel':
                delta = kwargs.get('delta', 0)
                win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, int(delta), 0)
        
        except Exception as e:
            logger.error(f"Error handling mouse event: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def move_mouse(self, x: float, y: float) -> None:
        """Move mouse to relative position (0-1)"""
        try:
            # Initialize COM for this method
            pythoncom.CoInitialize()
            
            # Get screen dimensions
            screen_width = win32api.GetSystemMetrics(win32con.SM_CXSCREEN)
            screen_height = win32api.GetSystemMetrics(win32con.SM_CYSCREEN)
            
            # Convert normalized coordinates to screen coordinates
            screen_x = int(x * screen_width)
            screen_y = int(y * screen_height)
            
            # Set cursor position directly
            win32api.SetCursorPos((screen_x, screen_y))
            
        except Exception as e:
            logger.error(f"Error moving mouse: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def click_mouse(self, x: float, y: float, button: int = 0) -> None:
        """Perform mouse click at position"""
        try:
            pythoncom.CoInitialize()
            # Move mouse to position first
            self.move_mouse(x, y)
            
            # Map button numbers to win32 events
            button_map = {
                0: (win32con.MOUSEEVENTF_LEFTDOWN, win32con.MOUSEEVENTF_LEFTUP),
                1: (win32con.MOUSEEVENTF_MIDDLEDOWN, win32con.MOUSEEVENTF_MIDDLEUP),
                2: (win32con.MOUSEEVENTF_RIGHTDOWN, win32con.MOUSEEVENTF_RIGHTUP)
            }
            
            if button in button_map:
                down_event, up_event = button_map[button]
                win32api.mouse_event(down_event, 0, 0, 0, 0)
                time.sleep(0.01)  # Small delay between down and up
                win32api.mouse_event(up_event, 0, 0, 0, 0)
        except Exception as e:
            logger.error(f"Error clicking mouse: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def mouse_down(self, x: float, y: float, button: int = 0) -> None:
        """Press mouse button down"""
        try:
            pythoncom.CoInitialize()
            self.move_mouse(x, y)
            button_map = {
                0: win32con.MOUSEEVENTF_LEFTDOWN,
                1: win32con.MOUSEEVENTF_MIDDLEDOWN,
                2: win32con.MOUSEEVENTF_RIGHTDOWN
            }
            if button in button_map:
                win32api.mouse_event(button_map[button], 0, 0, 0, 0)
        except Exception as e:
            logger.error(f"Error in mouse down: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def mouse_up(self, x: float, y: float, button: int = 0) -> None:
        """Release mouse button"""
        try:
            pythoncom.CoInitialize()
            self.move_mouse(x, y)
            button_map = {
                0: win32con.MOUSEEVENTF_LEFTUP,
                1: win32con.MOUSEEVENTF_MIDDLEUP,
                2: win32con.MOUSEEVENTF_RIGHTUP
            }
            if button in button_map:
                win32api.mouse_event(button_map[button], 0, 0, 0, 0)
        except Exception as e:
            logger.error(f"Error in mouse up: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def scroll_mouse(self, delta: int) -> None:
        """Scroll mouse wheel"""
        try:
            pythoncom.CoInitialize()
            win32api.mouse_event(win32con.MOUSEEVENTF_WHEEL, 0, 0, delta, 0)
        except Exception as e:
            logger.error(f"Error scrolling mouse: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def send_key(self, key: str, down: bool = True) -> None:
        """Send keyboard event"""
        try:
            pythoncom.CoInitialize()
            # Handle special key combinations
            if '+' in key:
                parts = key.split('+')
                if down:
                    for part in parts:
                        if part in self.VIRTUAL_KEYS:
                            win32api.keybd_event(self.VIRTUAL_KEYS[part], 0, 0, 0)
                else:
                    for part in reversed(parts):
                        if part in self.VIRTUAL_KEYS:
                            win32api.keybd_event(self.VIRTUAL_KEYS[part], 0, win32con.KEYEVENTF_KEYUP, 0)
                return

            # Handle single keys
            if key in self.VIRTUAL_KEYS:
                vk_code = self.VIRTUAL_KEYS[key]
                flags = 0 if down else win32con.KEYEVENTF_KEYUP
                win32api.keybd_event(vk_code, 0, flags, 0)
            else:
                # For characters not in virtual keys, use shell.SendKeys
                if down:  # Only send on key down to avoid duplicates
                    self.shell.SendKeys(key)
        except Exception as e:
            logger.error(f"Error sending key {key}: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def copy_to_clipboard(self) -> None:
        """Simulate Ctrl+C"""
        try:
            pythoncom.CoInitialize()
            self.send_key('Control', True)
            self.send_key('c', True)
            time.sleep(0.1)
            self.send_key('c', False)
            self.send_key('Control', False)
        except Exception as e:
            logger.error(f"Error copying to clipboard: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def paste_from_clipboard(self) -> None:
        """Simulate Ctrl+V"""
        try:
            pythoncom.CoInitialize()
            self.send_key('Control', True)
            self.send_key('v', True)
            time.sleep(0.1)
            self.send_key('v', False)
            self.send_key('Control', False)
        except Exception as e:
            logger.error(f"Error pasting from clipboard: {str(e)}")
        finally:
            pythoncom.CoUninitialize()

    def get_clipboard_text(self) -> str:
        """Get text from clipboard"""
        try:
            pythoncom.CoInitialize()
            win32clipboard.OpenClipboard()
            try:
                if win32clipboard.IsClipboardFormatAvailable(win32con.CF_TEXT):
                    return win32clipboard.GetClipboardData(win32con.CF_TEXT).decode('utf-8')
                return ""
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.error(f"Error getting clipboard text: {str(e)}")
            return ""
        finally:
            pythoncom.CoUninitialize()

    def set_clipboard_text(self, text: str) -> None:
        """Set text to clipboard"""
        try:
            pythoncom.CoInitialize()
            win32clipboard.OpenClipboard()
            try:
                win32clipboard.EmptyClipboard()
                win32clipboard.SetClipboardText(text, win32con.CF_TEXT)
            finally:
                win32clipboard.CloseClipboard()
        except Exception as e:
            logger.error(f"Error setting clipboard text: {str(e)}")
        finally:
            pythoncom.CoUninitialize()
