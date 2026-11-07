import http from 'k6/http';
import { check, sleep } from 'k6';

/**
 * ==============================================================================
 * KỊCH BẢN KIỂM THỬ TẢI HỆ THỐNG (LOAD TESTING)
 * Đề tài: Xây dựng nền tảng GitOps trên Kubernetes tích hợp AI Agent hỗ trợ vận hành
 * Sinh viên: Đinh Hồng Phong — MSSV: 24TX810013
 * 
 * Thông số kỹ thuật:
 * - Lưu lượng kiểm thử: Tối đa 30 Virtual Users (VUs)
 * - Thời gian thực thi: 60 giây (Giai đoạn tăng tải, duy trì và giảm tải)
 * - Chỉ số đánh giá (SLO):
 *   + Tỷ lệ yêu cầu lỗi (http_req_failed) < 1.0%
 *   + Thời gian phản hồi 95% yêu cầu (http_req_duration p95) < 300ms
 * ==============================================================================
 */

export const options = {
  stages: [
    { duration: '15s', target: 20 },  // Giai đoạn 1: Tăng tải lên 20 VUs
    { duration: '30s', target: 30 },  // Giai đoạn 2: Duy trì mức tải 30 VUs
    { duration: '15s', target: 0 },   // Giai đoạn 3: Giảm tải về 0
  ],

  thresholds: {
    http_req_failed: ['rate<0.01'],    // Ngưỡng tỷ lệ lỗi < 1%
    http_req_duration: ['p(95)<300'],  // Ngưỡng độ trễ p95 < 300ms
  },
};

const TARGET_URL = 'https://app.phongdinh.info.vn/';

export default function () {
  const params = {
    headers: {
      'User-Agent': 'k6-load-test/1.0 (Student: 24TX810013)',
      'X-Student-Id': '24TX810013',
    },
    timeout: '5s',
  };

  const response = http.get(TARGET_URL, params);

  check(response, {
    'Trạng thái HTTP 200': (r) => r.status === 200,
    'Thời gian đáp ứng < 300ms': (r) => r.timings.duration < 300,
  });

  sleep(0.1);
}
