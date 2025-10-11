import React from 'react';

const CertificateList = ({ certifications }) => {
  if (!certifications || certifications.length === 0) {
    return <p>You have no registered certifications.</p>;
  }

  return (
    <table>
      <thead>
        <tr>
          <th>Certification Name</th>
          <th>Issuing Organization</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {certifications.map(cert => (
          <tr key={cert.id}>
            <td>{cert.name}</td>
            <td>{cert.issuer}</td>
            <td>{cert.status}</td>
            <td>
              <button>View Details</button>
              <button>Download</button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
};

export default CertificateList;