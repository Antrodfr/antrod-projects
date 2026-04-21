interface BackgroundSelectorProps {
  backgroundType: 'transparent' | 'color'
  backgroundColor: string
  onTypeChange: (type: 'transparent' | 'color') => void
  onColorChange: (color: string) => void
}

export default function BackgroundSelector({
  backgroundType,
  backgroundColor,
  onTypeChange,
  onColorChange
}: BackgroundSelectorProps) {
  return (
    <div className="background-selector">
      <h3>Background Options</h3>
      <div className="bg-options">
        <label className={`bg-option ${backgroundType === 'transparent' ? 'bg-option--active' : ''}`}>
          <input
            type="radio"
            name="bgType"
            value="transparent"
            checked={backgroundType === 'transparent'}
            onChange={() => onTypeChange('transparent')}
          />
          <div className="bg-option-preview bg-transparent-preview" />
          <span>Transparent</span>
          <small>Saves as WebM</small>
        </label>

        <label className={`bg-option ${backgroundType === 'color' ? 'bg-option--active' : ''}`}>
          <input
            type="radio"
            name="bgType"
            value="color"
            checked={backgroundType === 'color'}
            onChange={() => onTypeChange('color')}
          />
          <div
            className="bg-option-preview"
            style={{ backgroundColor }}
          />
          <span>Solid Color</span>
          <small>Saves as MP4</small>
        </label>
      </div>

      {backgroundType === 'color' && (
        <div className="color-picker-row">
          <label>
            Pick a color:
            <input
              type="color"
              value={backgroundColor}
              onChange={(e) => onColorChange(e.target.value)}
            />
          </label>
          <div className="color-presets">
            {['#00ff00', '#0000ff', '#ffffff', '#000000', '#ff0000', '#808080'].map((c) => (
              <button
                key={c}
                className={`color-preset ${backgroundColor === c ? 'color-preset--active' : ''}`}
                style={{ backgroundColor: c }}
                onClick={() => onColorChange(c)}
                title={c}
              />
            ))}
          </div>
        </div>
      )}
    </div>
  )
}
