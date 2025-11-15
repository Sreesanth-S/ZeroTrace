// web_portal/backend/routes/auth.js
import express from 'express';
import supabaseClient from '../lib/supabaseClient.js';

const router = express.Router();

// Middleware to require authentication
export const requireAuth = async (req, res, next) => {
  const authHeader = req.headers.authorization;

  if (!authHeader || !authHeader.startsWith('Bearer ')) {
    return res.status(401).json({ error: 'Missing or invalid authorization header' });
  }

  const token = authHeader.split(' ')[1];
  const user = await supabaseClient.verifyUserToken(token);

  if (!user) {
    return res.status(401).json({ error: 'Invalid token' });
  }

  req.user = user;
  next();
};

// Get current user info
router.get('/user', requireAuth, (req, res) => {
  res.json({
    user: {
      id: req.user.id,
      email: req.user.email,
      created_at: req.user.created_at
    }
  });
});

// Get user profile
router.get('/profile', requireAuth, async (req, res) => {
  try {
    const { data, error } = await supabaseClient.client
      .from('user_profiles')
      .select('*')
      .eq('id', req.user.id)
      .single();

    if (error) {
      console.error('Profile fetch error:', error);
      return res.status(500).json({ error: 'Failed to fetch profile' });
    }

    if (data) {
      res.json({ profile: data });
    } else {
      res.status(404).json({ profile: null });
    }
  } catch (error) {
    console.error('Profile fetch error:', error);
    res.status(500).json({ error: 'Failed to fetch profile' });
  }
});

// Update user profile
router.put('/profile', requireAuth, async (req, res) => {
  try {
    const allowedFields = ['full_name', 'organization', 'phone'];
    const updateData = {};

    allowedFields.forEach(field => {
      if (req.body[field] !== undefined) {
        updateData[field] = req.body[field];
      }
    });

    if (Object.keys(updateData).length === 0) {
      return res.status(400).json({ error: 'No valid fields to update' });
    }

    const { data, error } = await supabaseClient.client
      .from('user_profiles')
      .upsert({
        id: req.user.id,
        ...updateData
      })
      .select();

    if (error) {
      console.error('Profile update error:', error);
      return res.status(500).json({ error: 'Failed to update profile' });
    }

    res.json({
      message: 'Profile updated successfully',
      profile: data?.[0] || null
    });
  } catch (error) {
    console.error('Profile update error:', error);
    res.status(500).json({ error: 'Failed to update profile' });
  }
});

// Sign up user with profile creation
router.post('/signup', async (req, res) => {
  try {
    const { email, password, full_name } = req.body;

    // Validate required fields
    if (!email || !password || !full_name) {
      return res.status(400).json({ 
        error: 'email, password, and full_name are required' 
      });
    }

    const result = await supabaseClient.signupWithProfile(email, password, full_name);

    if (result.success) {
      res.status(201).json(result);
    } else {
      res.status(400).json({ error: result.error });
    }
  } catch (error) {
    console.error('Signup route error:', error);
    res.status(500).json({ error: 'Failed to create account' });
  }
});

export default router;