-- BlueZ and elogind are available in the managed tablet session.
-- Keep WirePlumber's stock Bluetooth audio policy enabled. MIDI remains off
-- because it has not been validated on this device.
bluez_monitor.enabled = true
bluez_midi_monitor.enabled = false
