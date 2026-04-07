export default function DashboardPage() {
  return (
    <div>
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Панель управления</h1>

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
        <DashboardCard title="Сотрудники" value="—" description="Активных" />
        <DashboardCard title="Совещания" value="—" description="На этой неделе" />
        <DashboardCard title="Задачи" value="—" description="В работе" />
        <DashboardCard title="Просрочено" value="—" description="Требует внимания" />
      </div>

      <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
        <h2 className="text-lg font-semibold text-gray-900 mb-4">Последние события</h2>
        <p className="text-gray-500">Пока нет данных для отображения.</p>
      </div>
    </div>
  );
}

function DashboardCard({
  title,
  value,
  description,
}: {
  title: string;
  value: string;
  description: string;
}) {
  return (
    <div className="bg-white rounded-xl shadow-sm border border-gray-200 p-6">
      <p className="text-sm font-medium text-gray-500">{title}</p>
      <p className="text-3xl font-bold text-gray-900 mt-1">{value}</p>
      <p className="text-sm text-gray-400 mt-1">{description}</p>
    </div>
  );
}
