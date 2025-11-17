// web_portal/backend/lib/supabaseClient.js
import { createClient } from '@supabase/supabase-js';

class SupabaseClient {
  constructor() {
    const supabaseUrl = process.env.SUPABASE_URL;
    const supabaseKey = process.env.SUPABASE_KEY;
    const supabaseServiceKey = process.env.SUPABASE_SERVICE_KEY;

    if (!supabaseUrl || !supabaseKey) {
      throw new Error('SUPABASE_URL and SUPABASE_KEY must be configured');
    }

    this.client = createClient(supabaseUrl, supabaseKey);

    if (supabaseServiceKey) {
      this.serviceClient = createClient(supabaseUrl, supabaseServiceKey);
    }
  }

  async verifyUserToken(token) {
    try {
      const { data: { user }, error } = await this.client.auth.getUser(token);
      
      if (error) {
        console.error('Token verification error:', error);
        return null;
      }
      
      return user;
    } catch (error) {
      console.error('Token verification error:', error);
      return null;
    }
  }

  async getCertificateById(certId) {
    try {
      const { data, error } = await this.client
        .from('certificates')
        .select('*')
        .eq('cert_id', certId)
        .limit(1)
        .maybeSingle();

      if (error) {
        console.error('Database query error:', error);
        return null;
      }

      return data;
    } catch (error) {
      console.error('Database query error:', error);
      return null;
    }
  }

  async getUserCertificates(userId, limit = 50, offset = 0) {
    try {
      const { data, error } = await this.client
        .from('certificates')
        .select('*')
        .eq('user_id', userId)
        .order('created_at', { ascending: false })
        .range(offset, offset + limit - 1);

      if (error) {
        console.error('Database query error:', error);
        return [];
      }

      return data || [];
    } catch (error) {
      console.error('Database query error:', error);
      return [];
    }
  }

  async insertVerificationLog(certId, result, ipAddress, userAgent) {
    try {
      const { error } = await this.client
        .from('verification_logs')
        .insert({
          cert_id: certId,
          verification_result: result,
          ip_address: ipAddress,
          user_agent: userAgent
        });

      if (error) {
        console.error('Log insert error:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Log insert error:', error);
      return false;
    }
  }

  async getCertificateFileUrl(userId, certId, fileType = 'pdf', bucketName = 'certificates') {
    try {
      const filePath = `${userId}/${certId}.${fileType}`;
      
      const { data, error } = await this.client.storage
        .from(bucketName)
        .createSignedUrl(filePath, 3600); // Valid for 1 hour

      if (error) {
        console.error('Storage URL error:', error);
        return null;
      }

      return data?.signedUrl || null;
    } catch (error) {
      console.error('Storage URL error:', error);
      return null;
    }
  }

  async updateCertificateStatus(certId, status) {
    try {
      const { error } = await this.client
        .from('certificates')
        .update({ status })
        .eq('cert_id', certId);

      if (error) {
        console.error('Update error:', error);
        return false;
      }

      return true;
    } catch (error) {
      console.error('Update error:', error);
      return false;
    }
  }

  async signupWithProfile(email, password, fullName) {
    try {
      if (!this.serviceClient) {
        throw new Error('SUPABASE_SERVICE_KEY not configured');
      }

      // Sign up user
      const { data: authData, error: authError } = await this.serviceClient.auth.signUp({
        email,
        password,
        options: {
          data: {
            full_name: fullName,
          }
        }
      });

      if (authError) throw authError;

      if (authData.user) {
        // Create user profile
        const { error: profileError } = await this.serviceClient
          .from('user_profiles')
          .insert({
            id: authData.user.id,
            full_name: fullName
          });

        if (profileError) {
          console.error('Profile creation error:', profileError);
        }

        return {
          success: true,
          user: {
            id: authData.user.id,
            email: authData.user.email,
            created_at: authData.user.created_at
          },
          message: 'User created successfully. Please check your email to verify your account.'
        };
      }

      return {
        success: false,
        error: 'Failed to create user'
      };
    } catch (error) {
      console.error('Signup error:', error);
      return {
        success: false,
        error: error.message || 'Signup failed'
      };
    }
  }
}

// Create singleton instance
const supabaseClient = new SupabaseClient();

export default supabaseClient;