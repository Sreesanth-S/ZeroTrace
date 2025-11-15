import React, { useState } from 'react';
import CertificateList from './CertificateList';

const UserDashboard = ({ userName = "User" }) => {
  // const [certifications, setCertifications] = useState([
  //   { id: 'cert-12345', name: 'React Developer', issuer: 'Meta', status: 'Verified', url: 'https://your-domain.com/verify?id=cert-12345' },
  //   { id: 'cert-67890', name: 'AWS Cloud Practitioner', issuer: 'Amazon', status: 'Pending', url: 'https://your-domain.com/verify?id=cert-67890' },
  // ]);

  return (
    <div className="dashboard-container">
      <h1>Welcome back, {userName}!</h1>
      <section className="my-certifications-section">
        <h2>My Verified Certifications</h2>
        <CertificateList certifications={certifications} />
      </section>

      <section className="submit-certification-section">
        <h2>Submit a New Certificate</h2>
        <p>Use the options below to upload a new certificate for verification.</p>
        <div className="upload-options">
          <div className="option">
            <h3>Upload File</h3>
            <input type="file" />
            <button>Upload</button>
          </div>
          <div className="option">
            <h3>Manual Input</h3>
            <input type="text" placeholder="Certificate ID" />
            <button>Submit</button>
          </div>
        </div>
      </section>
      
      {certifications.map(cert => (
        <div key={cert.id} className="certificate-qr-container">
          <h3>QR Code for {cert.name}</h3>
          <p>This QR code links to your certificate's verification page.</p>
          <QrGenerator data={cert.url} />
        </div>
      ))}
    </div>
  );
};

export default UserDashboard;