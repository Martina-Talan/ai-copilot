import request from 'supertest';
import app from '../../server';
import fs from 'fs';

jest.mock('fs');
jest.mock('tiktoken');

jest.mock('pdfjs-dist', () => ({
  getDocument: jest.fn(() => ({
    promise: Promise.resolve({
      numPages: 2,
      getPage: jest.fn((num) => Promise.resolve({
        getTextContent: jest.fn(() =>
          Promise.resolve({
            items: [
              { str: `This is page ${num}` }
            ]
          })
        )
      }))
    })
  }))
}));
jest.mock('tiktoken');

describe('POST /view-pdf', () => {
  it('should return parsed PDF pages', async () => {
    (fs.readFileSync as jest.Mock).mockReturnValue(Buffer.from('dummy pdf'));

    const res = await request(app)
      .post('/view-pdf')
      .send({ path: 'fake.pdf' });

    expect(res.statusCode).toBe(200);
    expect(res.body.pages).toHaveLength(2);
    expect(res.body.pages[0].content).toContain('This is page 1');
  });

  it('should return 500 if error occurs', async () => {
    (fs.readFileSync as jest.Mock).mockImplementation(() => {
      throw new Error('fail');
    });

    const res = await request(app)
      .post('/view-pdf')
      .send({ path: 'fail.pdf' });

    expect(res.statusCode).toBe(500);
    expect(res.body).toHaveProperty('error');
  });
});
