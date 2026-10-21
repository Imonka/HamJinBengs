import { Tabs, TabsList, TabsTrigger, TabsContent } from "@/components/ui/tabs";
import { PageHeader } from "@/components/kit";
import { RolesTab } from "@/modules/people";
import { PatternsTab, RulesTab } from "@/modules/scheduling";

export default function Setup() {
  return (
    <div>
      <PageHeader eyebrow="Setup" title="The scheduling model" sub="Roles, the shifts you need each week, and the working-time rules the roster and cover suggestions must respect." />
      <Tabs defaultValue="patterns">
        <TabsList className="mb-5">
          <TabsTrigger value="patterns" data-testid="tab-patterns">Shift patterns</TabsTrigger>
          <TabsTrigger value="roles" data-testid="tab-roles">Roles</TabsTrigger>
          <TabsTrigger value="rules" data-testid="tab-rules">Rules & branch</TabsTrigger>
        </TabsList>
        <TabsContent value="patterns"><PatternsTab /></TabsContent>
        <TabsContent value="roles"><RolesTab /></TabsContent>
        <TabsContent value="rules"><RulesTab /></TabsContent>
      </Tabs>
    </div>
  );
}
