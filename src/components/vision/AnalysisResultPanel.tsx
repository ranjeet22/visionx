import React, { useState } from 'react';
import {
  CheckCircle2,
  AlertOctagon,
  ChevronDown,
  ChevronUp,
  Sparkles,
  Info,
  RefreshCw,
  MessageSquare,
  Compass,
  Layers,
  Repeat,
  ChevronLeft,
  ChevronRight,
  ShieldCheck,
  AlertTriangle,
  User,
} from 'lucide-react';
import { Badge } from '../ui/Badge';
import { Button } from '../ui/Button';
import type { DetectedWasteObject } from '../../types';
import './AnalysisResultPanel.css';

interface AnalysisResultPanelProps {
  selectedObject: DetectedWasteObject | null;
  totalDetections: number;
  currentIndex: number;
  isAnalyzing: boolean;
  hasAnalyzed: boolean;
  onSelectNext?: () => void;
  onSelectPrev?: () => void;
  onReset: () => void;
  onOpenAssistant: () => void;
}

export const AnalysisResultPanel: React.FC<AnalysisResultPanelProps> = ({
  selectedObject,
  totalDetections,
  currentIndex,
  isAnalyzing,
  hasAnalyzed,
  onSelectNext,
  onSelectPrev,
  onReset,
  onOpenAssistant,
}) => {
  const [whyExpanded, setWhyExpanded] = useState(false);

  // State 1: Analyzing Loading State
  if (isAnalyzing) {
    return (
      <div className="analysis-panel-card panel-loading">
        <div className="loading-content-box">
          <div className="loading-icon-pulse">
            <RefreshCw size={36} strokeWidth={2.5} className="spin-icon" />
          </div>
          <Badge variant="sun" size="sm">
            RUNNING DUAL-MODEL VISION
          </Badge>
          <h3 className="loading-title">Analyzing Image with VisionX Pipeline...</h3>
          <p className="loading-desc">
            Executing Ultralytics Person Detection and Roboflow Pretrained Waste Detection simultaneously.
          </p>
          <div className="loading-steps-ticker">
            <span>[1/3] Ultralytics Person Detector (COCO Class 0)</span>
            <span>[2/3] Roboflow Pretrained Waste Detector</span>
            <span>[3/3] Merging normalized detections &amp; disposal rules</span>
          </div>
        </div>
      </div>
    );
  }

  // State 2: Before Image is Captured / Analyzed
  if (!hasAnalyzed) {
    return (
      <div className="analysis-panel-card panel-empty">
        <div className="empty-content-box">
          <div className="empty-icon-circle">
            <Compass size={36} strokeWidth={2.5} />
          </div>
          <Badge variant="ink" size="sm">
            AWAITING INPUT
          </Badge>
          <h3 className="empty-title">Your results will appear here</h3>
          <p className="empty-desc">
            Capture a live video frame or upload an image, then press <strong>Run Detection</strong> to inspect dual-model vision predictions and disposal intelligence.
          </p>
          <div className="empty-checklist-hint">
            <div className="hint-row">
              <span className="hint-num">1</span>
              <span>Input photo via webcam or file upload</span>
            </div>
            <div className="hint-row">
              <span className="hint-num">2</span>
              <span>Execute dual-model pipeline (Person + Waste)</span>
            </div>
            <div className="hint-row">
              <span className="hint-num">3</span>
              <span>Select objects to inspect recycling steps &amp; ask AI</span>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // State 3: Analyzed but 0 Objects Detected
  if (hasAnalyzed && !selectedObject) {
    return (
      <div className="analysis-panel-card panel-empty">
        <div className="empty-content-box">
          <div className="empty-icon-circle" style={{ backgroundColor: '#FFE6EE' }}>
            <AlertTriangle size={36} strokeWidth={2.5} style={{ color: 'var(--pink)' }} />
          </div>
          <Badge variant="pink" size="sm">
            NO OBJECTS DETECTED
          </Badge>
          <h3 className="empty-title">No relevant objects detected</h3>
          <p className="empty-desc">
            The dual-model vision pipeline did not detect any people or recognized waste items above the confidence threshold in this frame.
          </p>
          <div className="empty-checklist-hint">
            <div className="hint-row">
              <span className="hint-num">•</span>
              <span>Ensure adequate ambient lighting to avoid shadows</span>
            </div>
            <div className="hint-row">
              <span className="hint-num">•</span>
              <span>Try placing the waste item in the center of the frame</span>
            </div>
            <div className="hint-row">
              <span className="hint-num">•</span>
              <span>Lower the confidence threshold filter (e.g. 15%)</span>
            </div>
          </div>
          <div style={{ marginTop: '18px', width: '100%' }}>
            <Button
              variant="secondary"
              size="md"
              onClick={onReset}
              icon={<RefreshCw size={16} strokeWidth={2.5} />}
              className="btn-scan-another"
            >
              Try Another Image
            </Button>
          </div>
        </div>
      </div>
    );
  }

  // State 4: Active Object Selected
  const obj = selectedObject!;
  const isPerson =
    obj.model_source === 'ultralytics_person' ||
    obj.model_class_name === 'person' ||
    obj.waste_category === 'non_waste' ||
    obj.waste_category === null;

  const getCategoryBadgeVariant = (cat?: string | null) => {
    if (isPerson) return 'ink';
    switch (cat) {
      case 'recyclable':
        return 'lime';
      case 'organic':
        return 'lime';
      case 'special-handling':
        return 'pink';
      case 'residual':
        return 'ink';
      default:
        return 'uncertain';
    }
  };

  return (
    <div className="analysis-panel-card panel-result">
      {/* Result Card Top Bar */}
      <div className="result-panel-header">
        <div className="result-badges-row">
          <Badge variant={getCategoryBadgeVariant(obj.waste_category)} size="md">
            {isPerson ? 'CATEGORY: NON-WASTE (PERSON)' : `CATEGORY: ${(obj.waste_category || 'UNCERTAIN').toUpperCase()}`}
          </Badge>

          <Badge variant="sun" size="sm">
            {Math.round(obj.confidence * 100)}% CONFIDENCE
          </Badge>

          <Badge
            variant={obj.mapping_status === 'verified' ? 'lime' : 'uncertain'}
            size="sm"
          >
            {isPerson
              ? 'PERSON VERIFIED'
              : obj.mapping_status === 'verified'
              ? 'VERIFIED MAPPING'
              : 'UNVERIFIED CLASS'}
          </Badge>
        </div>

        <div className="result-simulation-tag">
          <Badge variant="ink" size="sm">
            {obj.model_source === 'ultralytics_person'
              ? 'ULTRALYTICS COCO'
              : obj.model_source === 'roboflow_waste'
              ? 'ROBOFLOW PRETRAINED'
              : 'VISIONX DETECTOR'}
          </Badge>
        </div>
      </div>

      {/* Multi-Item Object Navigator Bar */}
      {totalDetections > 1 && (
        <div className="multi-object-nav-bar">
          <div className="nav-counter-tag">
            <Layers size={14} strokeWidth={2.5} />
            <span>
              OBJECT {currentIndex + 1} OF {totalDetections}: {obj.display_name}
            </span>
          </div>
          <div className="nav-arrow-buttons">
            <button
              type="button"
              className="nav-btn"
              onClick={onSelectPrev}
              disabled={currentIndex <= 0}
              aria-label="Previous object"
            >
              <ChevronLeft size={14} />
              <span>Prev</span>
            </button>
            <button
              type="button"
              className="nav-btn"
              onClick={onSelectNext}
              disabled={currentIndex >= totalDetections - 1}
              aria-label="Next object"
            >
              <span>Next</span>
              <ChevronRight size={14} />
            </button>
          </div>
        </div>
      )}

      <div className="result-panel-body">
        {/* Title and Material Info */}
        <div className="result-title-section">
          <h3 className="result-display-name">
            {isPerson && <User size={22} style={{ display: 'inline', marginRight: 8, verticalAlign: 'text-bottom' }} />}
            {obj.display_name}
          </h3>

          {!isPerson ? (
            <>
              <div className="result-material-pill">
                <Layers size={14} strokeWidth={2.5} />
                <span className="material-label">MATERIAL:</span>
                <span className="material-value">{obj.material || 'Mixed / Unspecified'}</span>
              </div>
              <p className="material-caveat-text">
                {obj.material_verified
                  ? 'Material classification confirmed from standard waste taxonomy.'
                  : 'Visual appearance indicates this material. Polymer resin chemistry is unverified without physical stamp inspection.'}
              </p>
            </>
          ) : (
            <div className="result-material-pill" style={{ backgroundColor: '#EEF2FF', borderColor: '#C7D2FE' }}>
              <User size={14} strokeWidth={2.5} />
              <span className="material-label" style={{ color: '#4338CA' }}>CLASSIFICATION:</span>
              <span className="material-value" style={{ color: '#312E81' }}>Human / Non-Waste</span>
            </div>
          )}
        </div>

        {/* Action Callout */}
        <div className="result-action-callout" style={isPerson ? { backgroundColor: '#EEF2FF', borderColor: '#6366F1' } : undefined}>
          <div className="action-callout-header">
            {isPerson ? <User size={18} strokeWidth={2.5} /> : <CheckCircle2 size={18} strokeWidth={2.5} />}
            <span>{isPerson ? 'DETECTION STATUS' : 'RECOMMENDED NEXT STEP'}</span>
          </div>
          <p className="action-callout-text">
            {isPerson
              ? 'Person detected. This is not a waste item, so waste disposal guidance does not apply.'
              : obj.disposal_method || 'Inspect physically and check local municipal sorting regulations.'}
          </p>
        </div>

        {/* Preparation Checklist for Waste Items */}
        {!isPerson && obj.preparation_steps && obj.preparation_steps.length > 0 && (
          <div className="result-prep-section">
            <h4 className="prep-section-heading">Preparation Steps:</h4>
            <ol className="prep-ordered-list">
              {obj.preparation_steps.map((step, idx) => (
                <li key={idx} className="prep-list-item">
                  <span className="item-step-num">{idx + 1}</span>
                  <span className="item-step-text">{step}</span>
                </li>
              ))}
            </ol>
          </div>
        )}

        {/* Recycling / Sorting Guidance for Waste Items */}
        {!isPerson && obj.recycling_guidance && (
          <div className="result-guidance-card">
            <div className="guidance-title">
              <ShieldCheck size={16} strokeWidth={2.5} />
              <span>Recycling &amp; Sorting Guidance:</span>
            </div>
            <p className="guidance-text">{obj.recycling_guidance}</p>
          </div>
        )}

        {/* Reusability Potential (if available) */}
        {!isPerson && obj.reusability && (
          <div className="result-reusability-row">
            <Repeat size={16} strokeWidth={2.5} style={{ flexShrink: 0, marginTop: '2px' }} />
            <div>
              <strong>Reusability Potential: </strong>
              <span>{obj.reusability}</span>
            </div>
          </div>
        )}

        {/* Contamination Notice */}
        {!isPerson && obj.contamination_warning && (
          <div className="result-warning-box">
            <AlertOctagon size={18} strokeWidth={2.5} className="warning-icon" />
            <div>
              <strong className="warning-heading">Contamination Warning: </strong>
              <span className="warning-body">{obj.contamination_warning}</span>
            </div>
          </div>
        )}

        {/* Collapsible Environmental Rationale & Source */}
        {!isPerson && obj.environmental_impact && (
          <div className="result-collapsible-wrapper">
            <button
              type="button"
              className="collapsible-toggle-btn"
              onClick={() => setWhyExpanded(!whyExpanded)}
              aria-expanded={whyExpanded}
              aria-controls="why-explanation-panel"
            >
              <span className="toggle-label-group">
                <Info size={16} strokeWidth={2.5} />
                <span>Why this recommendation matters</span>
              </span>
              {whyExpanded ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
            </button>

            {whyExpanded && (
              <div id="why-explanation-panel" className="collapsible-content-box">
                <p className="environmental-text">{obj.environmental_impact}</p>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap', marginTop: '8px' }}>
                  <div className="policy-status-pill">
                    <span className="status-label">POLICY:</span>
                    <span className="status-text">
                      {obj.policy_status === 'verified-local'
                        ? 'Verified Local Policy'
                        : 'GENERAL GUIDANCE · LOCAL RULES MAY VARY'}
                    </span>
                  </div>
                  {obj.source && (
                    <div className="policy-status-pill">
                      <span className="status-label">SOURCE:</span>
                      <span className="status-text">{obj.source}</span>
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>
        )}

        {/* Assistant Follow-up Trigger Card (Sky Blue) */}
        <div className="result-assistant-callout">
          <div className="assistant-callout-left">
            <Sparkles size={18} strokeWidth={2.5} className="sparkle-icon" />
            <div>
              <strong>{isPerson ? 'Have a question about this detection?' : 'Have a question about this item?'}</strong>
              <p>
                {isPerson
                  ? 'Ask the VisionX assistant about the detections in this frame or voice your questions.'
                  : 'Ask the VisionX assistant for disposal details, local rules, or voice your questions.'}
              </p>
            </div>
          </div>
          <Button
            variant="primary"
            size="sm"
            onClick={onOpenAssistant}
            icon={<MessageSquare size={16} strokeWidth={2.5} />}
          >
            Ask VisionX
          </Button>
        </div>

        {/* Reset / Scan Another Action */}
        <div className="result-footer-actions">
          <Button
            variant="secondary"
            size="md"
            onClick={onReset}
            icon={<RefreshCw size={16} strokeWidth={2.5} />}
            className="btn-scan-another"
          >
            Scan Another Item
          </Button>
        </div>
      </div>
    </div>
  );
};
