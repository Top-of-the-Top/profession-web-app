import { useCallback, useEffect, useMemo, useRef, useState, type CSSProperties } from 'react';
import type { MutableRefObject } from 'react';
import { $generateHtmlFromNodes, $generateNodesFromDOM } from '@lexical/html';
import {
  INSERT_ORDERED_LIST_COMMAND,
  INSERT_UNORDERED_LIST_COMMAND,
  ListItemNode,
  ListNode,
  REMOVE_LIST_COMMAND,
  $isListNode,
  registerList,
} from '@lexical/list';
import { LexicalComposer } from '@lexical/react/LexicalComposer';
import { useLexicalComposerContext } from '@lexical/react/LexicalComposerContext';
import { ContentEditable } from '@lexical/react/LexicalContentEditable';
import { LexicalErrorBoundary } from '@lexical/react/LexicalErrorBoundary';
import { HistoryPlugin } from '@lexical/react/LexicalHistoryPlugin';
import { OnChangePlugin } from '@lexical/react/LexicalOnChangePlugin';
import { RichTextPlugin } from '@lexical/react/LexicalRichTextPlugin';
import {
  $createHeadingNode,
  $createQuoteNode,
  $isHeadingNode,
  $isQuoteNode,
  HeadingNode,
  QuoteNode,
  type HeadingTagType,
} from '@lexical/rich-text';
import { $setBlocksType } from '@lexical/selection';
import { mergeRegister } from '@lexical/utils';
import {
  $createParagraphNode,
  $getRoot,
  $getSelection,
  $insertNodes,
  $isRangeSelection,
  COMMAND_PRIORITY_CRITICAL,
  COMMAND_PRIORITY_LOW,
  FORMAT_TEXT_COMMAND,
  INDENT_CONTENT_COMMAND,
  KEY_TAB_COMMAND,
  OUTDENT_CONTENT_COMMAND,
  SELECTION_CHANGE_COMMAND,
  type LexicalEditor,
} from 'lexical';
import {
  Bold,
  Heading1,
  Heading2,
  List,
  ListOrdered,
  Pilcrow,
  Quote,
  Underline,
} from 'lucide-react';
import { sanitizeEditorHtml } from '@shared/lib/html/sanitizeEditorHtml';
import { cn } from '@shared/lib/utils';
import styles from './RichTextEditor.module.css';

type BlockType = 'paragraph' | HeadingTagType | 'quote' | 'bullet' | 'number';
type RichTextEditorVariant = 'default' | 'compact';

interface RichTextEditorProps {
  value: string;
  onChange?: (value: string) => void;
  disabled?: boolean;
  placeholder?: string;
  className?: string;
  variant?: RichTextEditorVariant;
  hideToolbar?: boolean;
  contentFontSizePx?: number;
  contentLineHeight?: CSSProperties['lineHeight'];
}

const editorTheme = {
  paragraph: styles.paragraph,
  quote: styles.quote,
  heading: {
    h1: styles.heading1,
    h2: styles.heading2,
    h3: styles.heading3,
  },
  list: {
    nested: {
      listitem: styles.nestedListItem,
    },
    ol: styles.orderedList,
    ul: styles.unorderedList,
    listitem: styles.listItem,
  },
  text: {
    bold: styles.boldText,
    italic: styles.italicText,
    underline: styles.underlineText,
  },
};

function loadHtmlIntoEditor(editor: LexicalEditor, html: string) {
  editor.update(() => {
    const parser = new DOMParser();
    const dom = parser.parseFromString(sanitizeEditorHtml(html), 'text/html');
    const nodes = $generateNodesFromDOM(editor, dom);
    const root = $getRoot();
    root.clear();
    if (nodes.length > 0) {
      $insertNodes(nodes);
    }
    if (root.getChildrenSize() === 0) {
      root.append($createParagraphNode());
    }
  });
}

function getSelectedBlockType(): BlockType {
  const selection = $getSelection();
  if (!$isRangeSelection(selection)) return 'paragraph';

  const anchorNode = selection.anchor.getNode();
  const topLevelElement =
    anchorNode.getKey() === 'root'
      ? anchorNode
      : anchorNode.getTopLevelElementOrThrow();

  if ($isListNode(topLevelElement)) {
    const listType = topLevelElement.getListType();
    return listType === 'number' ? 'number' : 'bullet';
  }
  if ($isHeadingNode(topLevelElement)) return topLevelElement.getTag();
  if ($isQuoteNode(topLevelElement)) return 'quote';
  return 'paragraph';
}

function ListSetupPlugin() {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    return mergeRegister(
      registerList(editor),
      editor.registerCommand<KeyboardEvent>(
        KEY_TAB_COMMAND,
        (event) => {
          const blockType = getSelectedBlockType();
          if (blockType !== 'bullet' && blockType !== 'number') return false;
          event.preventDefault();
          editor.dispatchCommand(
            event.shiftKey ? OUTDENT_CONTENT_COMMAND : INDENT_CONTENT_COMMAND,
            undefined,
          );
          return true;
        },
        COMMAND_PRIORITY_CRITICAL,
      ),
    );
  }, [editor]);

  return null;
}

function EditableStatePlugin({ disabled }: { disabled: boolean }) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    editor.setEditable(!disabled);
  }, [disabled, editor]);

  return null;
}

function ExternalValuePlugin({
  value,
  latestHtmlRef,
}: {
  value: string;
  latestHtmlRef: MutableRefObject<string>;
}) {
  const [editor] = useLexicalComposerContext();

  useEffect(() => {
    if (value === latestHtmlRef.current) return;
    latestHtmlRef.current = value;
    loadHtmlIntoEditor(editor, value);
  }, [editor, latestHtmlRef, value]);

  return null;
}

function ToolbarPlugin({ disabled }: { disabled: boolean }) {
  const [editor] = useLexicalComposerContext();
  const [activeFormats, setActiveFormats] = useState({
    bold: false,
    underline: false,
  });
  const [blockType, setBlockType] = useState<BlockType>('paragraph');

  const updateToolbar = useCallback(() => {
    const selection = $getSelection();
    if ($isRangeSelection(selection)) {
      setActiveFormats({
        bold: selection.hasFormat('bold'),
        underline: selection.hasFormat('underline'),
      });
    }
    setBlockType(getSelectedBlockType());
  }, []);

  useEffect(() => {
    return mergeRegister(
      editor.registerUpdateListener(({ editorState }) => {
        editorState.read(updateToolbar);
      }),
      editor.registerCommand(
        SELECTION_CHANGE_COMMAND,
        () => {
          updateToolbar();
          return false;
        },
        COMMAND_PRIORITY_LOW,
      ),
    );
  }, [editor, updateToolbar]);

  const applyBlockType = (nextType: BlockType) => {
    if (disabled) return;

    if (nextType === 'bullet') {
      editor.dispatchCommand(
        blockType === 'bullet' ? REMOVE_LIST_COMMAND : INSERT_UNORDERED_LIST_COMMAND,
        undefined,
      );
      return;
    }

    if (nextType === 'number') {
      editor.dispatchCommand(
        blockType === 'number' ? REMOVE_LIST_COMMAND : INSERT_ORDERED_LIST_COMMAND,
        undefined,
      );
      return;
    }

    editor.update(() => {
      const selection = $getSelection();
      if (!$isRangeSelection(selection)) return;
      if (nextType === 'quote') {
        if (getSelectedBlockType() === 'quote') {
          $setBlocksType(selection, () => $createParagraphNode());
        } else {
          $setBlocksType(selection, () => $createQuoteNode());
        }
      } else if (nextType === 'paragraph') {
        $setBlocksType(selection, () => $createParagraphNode());
      } else {
        $setBlocksType(selection, () => $createHeadingNode(nextType));
      }
    });
  };

  return (
    <div className={styles.toolbar}>
      <button
        type="button"
        className={cn(styles.toolbarButton, activeFormats.bold && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'bold')}
        aria-label="Жирный"
      >
        <Bold size={16} />
      </button>
      <button
        type="button"
        className={cn(
          styles.toolbarButton,
          activeFormats.underline && styles.toolbarButtonActive,
        )}
        disabled={disabled}
        onClick={() => editor.dispatchCommand(FORMAT_TEXT_COMMAND, 'underline')}
        aria-label="Подчеркнутый"
      >
        <Underline size={16} />
      </button>
      <span className={styles.toolbarDivider} />
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'paragraph' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('paragraph')}
        aria-label="Обычный текст"
      >
        <Pilcrow size={16} />
      </button>
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'h1' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('h1')}
        aria-label="Заголовок 1"
      >
        <Heading1 size={16} />
      </button>
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'h2' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('h2')}
        aria-label="Заголовок 2"
      >
        <Heading2 size={16} />
      </button>
      <span className={styles.toolbarDivider} />
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'bullet' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('bullet')}
        aria-label="Маркированный список"
      >
        <List size={16} />
      </button>
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'number' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('number')}
        aria-label="Нумерованный список"
      >
        <ListOrdered size={16} />
      </button>
      <button
        type="button"
        className={cn(styles.toolbarButton, blockType === 'quote' && styles.toolbarButtonActive)}
        disabled={disabled}
        onClick={() => applyBlockType('quote')}
        aria-label="Цитата"
      >
        <Quote size={16} />
      </button>
    </div>
  );
}

export function RichTextEditor({
  value,
  onChange,
  disabled = false,
  placeholder = 'Введите текст',
  className,
  variant = 'default',
  hideToolbar = false,
  contentFontSizePx,
  contentLineHeight,
}: RichTextEditorProps) {
  const latestHtmlRef = useRef(value);
  const contentTypographyStyle = useMemo((): CSSProperties | undefined => {
    if (contentFontSizePx == null && contentLineHeight == null) return undefined;
    return {
      ...(contentFontSizePx != null ? { fontSize: `${contentFontSizePx}px` } : {}),
      ...(contentLineHeight != null ? { lineHeight: contentLineHeight } : {}),
    };
  }, [contentFontSizePx, contentLineHeight]);
  const initialConfig = useMemo(
    () => ({
      namespace: 'RichTextEditor',
      nodes: [HeadingNode, QuoteNode, ListNode, ListItemNode],
      theme: editorTheme,
      editable: !disabled,
      editorState: (editor: LexicalEditor) => {
        loadHtmlIntoEditor(editor, value);
      },
      onError(error: Error) {
        throw error;
      },
    }),
    [],
  );

  return (
    <LexicalComposer initialConfig={initialConfig}>
      <div
        className={cn(
          styles.editor,
          variant === 'compact' && styles.editorCompact,
          disabled && styles.editorDisabled,
          className,
        )}
      >
        <div className={styles.editorBody}>
          {!hideToolbar && (
            <div className={styles.toolbarFloat} data-rich-text-toolbar>
              <ToolbarPlugin disabled={disabled} />
            </div>
          )}
          <div className={styles.inputWrap}>
            <RichTextPlugin
              contentEditable={
                <ContentEditable
                  className={styles.contentEditable}
                  style={contentTypographyStyle}
                  aria-placeholder={placeholder}
                  placeholder={
                    <span className={styles.placeholder} style={contentTypographyStyle}>
                      {placeholder}
                    </span>
                  }
                />
              }
              ErrorBoundary={LexicalErrorBoundary}
            />
          </div>
        </div>
      </div>
      <HistoryPlugin />
      <ListSetupPlugin />
      <EditableStatePlugin disabled={disabled} />
      <ExternalValuePlugin value={value} latestHtmlRef={latestHtmlRef} />
      <OnChangePlugin
        ignoreSelectionChange
        onChange={(_, editor) => {
          editor.getEditorState().read(() => {
            const nextHtml = $generateHtmlFromNodes(editor, null);
            const sanitizedHtml = sanitizeEditorHtml(nextHtml);
            latestHtmlRef.current = sanitizedHtml;
            onChange?.(sanitizedHtml);
          });
        }}
      />
    </LexicalComposer>
  );
}
