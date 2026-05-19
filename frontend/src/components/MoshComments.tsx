/**
 * MoshComments — inline expanding thread under a post.
 *
 * - Fetches comments on first expand
 * - Composer at bottom (when expanded)
 * - Own comments get a delete button
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  View, Text, StyleSheet, TouchableOpacity, TextInput, ActivityIndicator, Alert,
} from 'react-native';
import { Ionicons } from '@expo/vector-icons';
import axios from 'axios';
import { useApp } from '../context/AppContext';

interface Comment {
  id: string;
  post_id: string;
  user_id: string;
  username: string;
  content: string;
  created_at: string;
}

const MAX_COMMENT = 200;

const relativeTime = (iso: string): string => {
  const s = Math.floor((Date.now() - new Date(iso).getTime()) / 1000);
  if (s < 60) return `${s}s`;
  if (s < 3600) return `${Math.floor(s / 60)}m`;
  if (s < 86400) return `${Math.floor(s / 3600)}h`;
  return `${Math.floor(s / 86400)}d`;
};

interface Props {
  postId: string;
  initialCount: number;
  onCountChange?: (newCount: number) => void;
}

export const MoshComments: React.FC<Props> = ({ postId, initialCount, onCountChange }) => {
  const { user, apiUrl } = useApp();
  const [expanded, setExpanded] = useState(false);
  const [comments, setComments] = useState<Comment[]>([]);
  const [loaded, setLoaded] = useState(false);
  const [loading, setLoading] = useState(false);
  const [text, setText] = useState('');
  const [sending, setSending] = useState(false);
  const [count, setCount] = useState(initialCount);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const res = await axios.get(`${apiUrl}/api/mosh/posts/${postId}/comments`);
      setComments(res.data);
      setLoaded(true);
    } catch {
      Alert.alert('Error', 'Failed to load comments.');
    } finally {
      setLoading(false);
    }
  }, [apiUrl, postId]);

  useEffect(() => {
    if (expanded && !loaded) load();
  }, [expanded, loaded, load]);

  const updateCount = (delta: number) => {
    const next = Math.max(0, count + delta);
    setCount(next);
    onCountChange?.(next);
  };

  const handleSubmit = async () => {
    if (!user) return;
    const trimmed = text.trim();
    if (!trimmed) return;
    setSending(true);
    try {
      const res = await axios.post(
        `${apiUrl}/api/mosh/posts/${postId}/comments`,
        { user_id: user.id, content: trimmed },
      );
      setComments((prev) => [...prev, res.data]);
      updateCount(1);
      setText('');
    } catch (e: any) {
      Alert.alert('Error', e?.response?.data?.detail || 'Failed to post.');
    } finally {
      setSending(false);
    }
  };

  const handleDelete = (commentId: string) => {
    if (!user) return;
    Alert.alert('Delete comment?', '', [
      { text: 'Cancel', style: 'cancel' },
      {
        text: 'Delete',
        style: 'destructive',
        onPress: async () => {
          try {
            await axios.delete(`${apiUrl}/api/mosh/comments/${commentId}`, {
              data: { user_id: user.id },
            });
            setComments((prev) => prev.filter((c) => c.id !== commentId));
            updateCount(-1);
          } catch (e: any) {
            Alert.alert('Error', e?.response?.data?.detail || 'Failed.');
          }
        },
      },
    ]);
  };

  return (
    <View>
      <TouchableOpacity
        style={styles.toggle}
        onPress={() => setExpanded((v) => !v)}
        testID={`mosh-comments-toggle-${postId}`}
      >
        <Ionicons
          name={expanded ? 'chatbubbles' : 'chatbubbles-outline'}
          size={14}
          color={expanded ? '#39ff14' : '#789'}
        />
        <Text style={[styles.toggleText, expanded && { color: '#39ff14' }]}>
          {count} {count === 1 ? 'comment' : 'comments'}
        </Text>
        <Ionicons
          name={expanded ? 'chevron-up' : 'chevron-down'}
          size={12}
          color="#789"
        />
      </TouchableOpacity>

      {expanded && (
        <View style={styles.thread}>
          {loading ? (
            <ActivityIndicator color="#39ff14" />
          ) : (
            <>
              {comments.length === 0 && (
                <Text style={styles.emptyComments}>Be the first to reply.</Text>
              )}
              {comments.map((c) => (
                <View key={c.id} style={styles.comment} testID={`mosh-comment-${c.id}`}>
                  <View style={styles.commentHead}>
                    <Text style={styles.commentUser}>{c.username}</Text>
                    <Text style={styles.commentTime}>{relativeTime(c.created_at)}</Text>
                    {user && c.user_id === user.id && (
                      <TouchableOpacity
                        onPress={() => handleDelete(c.id)}
                        testID={`mosh-comment-delete-${c.id}`}
                        style={{ marginLeft: 'auto' }}
                      >
                        <Ionicons name="trash-outline" size={12} color="#ff6b6b" />
                      </TouchableOpacity>
                    )}
                  </View>
                  <Text style={styles.commentContent}>{c.content}</Text>
                </View>
              ))}
              <View style={styles.composer}>
                <TextInput
                  style={styles.composerInput}
                  value={text}
                  onChangeText={setText}
                  placeholder="Write a reply..."
                  placeholderTextColor="#555"
                  multiline
                  maxLength={MAX_COMMENT}
                  testID={`mosh-comment-input-${postId}`}
                />
                <TouchableOpacity
                  style={[styles.sendBtn, (!text.trim() || sending) && { opacity: 0.4 }]}
                  onPress={handleSubmit}
                  disabled={!text.trim() || sending}
                  testID={`mosh-comment-send-${postId}`}
                >
                  {sending ? (
                    <ActivityIndicator size="small" color="#000" />
                  ) : (
                    <Ionicons name="send" size={14} color="#000" />
                  )}
                </TouchableOpacity>
              </View>
            </>
          )}
        </View>
      )}
    </View>
  );
};

const styles = StyleSheet.create({
  toggle: {
    flexDirection: 'row',
    alignItems: 'center',
    gap: 4,
    alignSelf: 'flex-start',
    paddingHorizontal: 8,
    paddingVertical: 4,
    borderRadius: 6,
    marginTop: 6,
    borderWidth: 1,
    borderColor: 'rgba(255,255,255,0.08)',
  },
  toggleText: { color: '#789', fontSize: 12, fontWeight: '700' },
  thread: {
    marginTop: 8,
    paddingTop: 8,
    paddingLeft: 8,
    borderLeftWidth: 2,
    borderLeftColor: 'rgba(57,255,20,0.3)',
  },
  emptyComments: { color: '#555', fontSize: 11, fontStyle: 'italic', paddingVertical: 6 },
  comment: { paddingVertical: 6 },
  commentHead: { flexDirection: 'row', alignItems: 'center', gap: 6, marginBottom: 2 },
  commentUser: { color: '#9aff5a', fontSize: 11, fontWeight: '900' },
  commentTime: { color: '#456', fontSize: 10 },
  commentContent: { color: '#cde', fontSize: 12, lineHeight: 16 },
  composer: {
    flexDirection: 'row',
    alignItems: 'flex-end',
    gap: 6,
    marginTop: 8,
    paddingTop: 8,
    borderTopWidth: 1,
    borderTopColor: 'rgba(255,255,255,0.05)',
  },
  composerInput: {
    flex: 1,
    color: '#fff',
    fontSize: 12,
    paddingHorizontal: 8,
    paddingVertical: 6,
    minHeight: 32,
    maxHeight: 80,
    backgroundColor: 'rgba(0,0,0,0.3)',
    borderRadius: 6,
    borderWidth: 1,
    borderColor: 'rgba(57,255,20,0.2)',
  },
  sendBtn: {
    width: 32,
    height: 32,
    borderRadius: 16,
    backgroundColor: '#39ff14',
    alignItems: 'center',
    justifyContent: 'center',
  },
});

export default MoshComments;
